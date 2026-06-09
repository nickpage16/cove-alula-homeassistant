"""Config flow for Cove (Alula) Alarm."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_EMAIL, CONF_PASSWORD, CONF_PIN, CONF_TOKEN, DOMAIN
from .covealula import CoveAlulaAuthError, CoveAlulaClient, CoveAlulaError

STEP_USER = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_PIN): str,
    }
)


class CoveAlulaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the UI config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = CoveAlulaClient(session=session)
            try:
                await client.async_login(
                    user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
                )
                await client.async_get_self()
            except CoveAlulaAuthError:
                errors["base"] = "invalid_auth"
            except CoveAlulaError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_EMAIL],
                    data={
                        CONF_EMAIL: user_input[CONF_EMAIL],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_PIN: user_input[CONF_PIN],
                        CONF_TOKEN: client.token.as_dict(),
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER, errors=errors
        )
