"""DataUpdateCoordinator that owns the Cove/Alula client and live websocket."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_TOKEN,
    DOMAIN,
    POLL_INTERVAL_SECONDS,
)
from .covealula import (
    CoveAlulaAuthError,
    CoveAlulaClient,
    CoveAlulaError,
    CoveToken,
    PanelState,
)

_LOGGER = logging.getLogger(__name__)


class CoveAlulaCoordinator(DataUpdateCoordinator[dict[str, PanelState]]):
    """Keeps panel state fresh from REST polling + websocket pushes."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=POLL_INTERVAL_SECONDS),
        )
        self.entry = entry
        session = async_get_clientsession(hass)

        token = None
        if entry.data.get(CONF_TOKEN):
            token = CoveToken.from_dict(entry.data[CONF_TOKEN])

        self.client = CoveAlulaClient(
            session=session,
            token=token,
            token_updated=self._persist_token,
            update_callback=self._on_push,
        )

    async def _persist_token(self, token: CoveToken) -> None:
        """Save the refreshed token into the config entry."""
        data = {**self.entry.data, CONF_TOKEN: token.as_dict()}
        self.hass.config_entries.async_update_entry(self.entry, data=data)

    def _on_push(self, panel: PanelState) -> None:
        """Websocket pushed new state -> notify entities immediately."""
        self.async_set_updated_data(dict(self.client.panels))

    async def async_setup(self) -> None:
        """Authenticate, discover panels, connect the socket, and subscribe for state."""
        try:
            if self.client.token.is_expired:
                if self.client.token.is_refreshable:
                    await self.client.async_refresh()
                else:
                    await self.client.async_login(
                        self.entry.data[CONF_EMAIL],
                        self.entry.data[CONF_PASSWORD],
                    )
            panels = await self.client.async_get_panels()
            await self.client.async_connect_ws()
            # Nothing pushes panel state until we subscribe + request a snapshot. This also
            # pulls the friendly name + zone list (names, config, live status).
            for panel in panels:
                await self.client.async_refresh_state(panel.device_id)
            # give the snapshot + zone responses a moment to arrive before we build entities
            await asyncio.sleep(3)
        except CoveAlulaAuthError as err:
            raise UpdateFailed(f"Cove/Alula authentication failed: {err}") from err
        except CoveAlulaError as err:
            raise UpdateFailed(f"Cove/Alula setup failed: {err}") from err

    async def _async_update_data(self) -> dict[str, PanelState]:
        """Backstop refresh. The websocket keeps state live and now reconciles on every
        reconnect, so this just ensures the socket is up and re-reads zone/panel status in
        case a push was ever missed. Transient failures keep the last known state rather
        than flapping every entity to 'unavailable'."""
        try:
            await self.client.async_connect_ws()  # reconnect if the socket dropped
            device_ids = list(self.client.panels)
            if not device_ids:
                # first run, or panels lost: (re)discover via REST
                panels = await self.client.async_get_panels()
                device_ids = [p.device_id for p in panels]
            for device_id in device_ids:
                await self.client.async_reconcile(device_id)
        except CoveAlulaAuthError:
            # token died and couldn't refresh -> try a full re-login once
            try:
                await self.client.async_login(
                    self.entry.data[CONF_EMAIL], self.entry.data[CONF_PASSWORD]
                )
                await self.client.async_connect_ws()
            except CoveAlulaError as err2:
                if self.client.panels:
                    _LOGGER.warning("re-auth failed, keeping last known state: %s", err2)
                    return dict(self.client.panels)
                raise UpdateFailed(f"re-auth failed: {err2}") from err2
        except CoveAlulaError as err:
            if self.client.panels:
                _LOGGER.debug("poll reconcile failed, keeping last known state: %s", err)
                return dict(self.client.panels)
            raise UpdateFailed(f"poll failed: {err}") from err
        return dict(self.client.panels)

    async def async_shutdown(self) -> None:
        await self.client.async_close()
