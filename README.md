# Cove (Alula) Alarm — Home Assistant integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/sam3gp8/cove-alula-homeassistant/actions/workflows/validate.yml/badge.svg)](https://github.com/sam3gp8/cove-alula-homeassistant/actions/workflows/validate.yml)
![version](https://img.shields.io/badge/version-0.9.1-blue.svg)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-FFDD00?logo=buymeacoffee&logoColor=black)](https://www.buymeacoffee.com/sam3gp8)

Control and monitor a **Cove** home-security system (built on the **Alula "Connect"**
cloud platform) from Home Assistant. Adds an `alarm_control_panel` entity that can arm
(home / away / night), disarm, and report live panel state.

This talks to the same `api.alula.net` cloud the official Cove Connect app uses, with
**your own** account credentials and PIN. It is cloud-based (`cloud_push` over a
WebSocket); there is no LAN/BLE local control yet.

> ⚠️ **This is a professionally-monitored alarm.** Arming, disarming, and alarm
> cancel/confirm generate **real central-station events**. Put your account on **test
> mode** with the monitoring provider while you set this up and validate it, and avoid
> rapid repeated login/PIN attempts (the service rate-limits with HTTP 429 and the panel
> has a keypad lockout).

---

## Install

### Option A — HACS (recommended)

This repo is a HACS **custom repository**. To add it:

1. In Home Assistant, open **HACS → ⋮ (top right) → Custom repositories**.
2. Repository: `https://github.com/sam3gp8/cove-alula-homeassistant` — Category: **Integration** — **Add**.
3. Search HACS for **Cove (Alula) Alarm**, open it, and click **Download**.
4. **Restart Home Assistant.**
5. Go to **Settings → Devices & Services → + Add Integration**, search for
   **“Cove (Alula) Alarm”**, and follow the prompts.

Or use the one-click link (opens the dialog pre-filled):

[![Open your Home Assistant instance and open a repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=sam3gp8&repository=cove-alula-homeassistant&category=integration)

### Option B — Manual

1. Copy the folder `custom_components/cove_alula` from this repo into your Home
   Assistant config directory, so you end up with:
   ```
   /config/custom_components/cove_alula/
   ```
2. Restart Home Assistant.
3. Add the integration from **Settings → Devices & Services** as above.

---

## Configuration

The setup dialog asks for three things:

| Field | What to enter |
|---|---|
| **Email or account number** | Your Cove login — an email **or** the account number (e.g. `C123456`). |
| **Password** | Your Cove account password. |
| **Arm/disarm PIN** | The user PIN you use on the keypad. Stored in HA and applied automatically so automations can arm/disarm without re-entering it. |

The integration logs in once, then persists a refresh token in the config entry so it
keeps working across restarts without re-authenticating.

### What you get

* An **Alarm Control Panel** entity supporting **Arm Home**, **Arm Away**, **Arm Night**,
  and **Disarm**. The device is named after your system (e.g. "My Home").
* A **binary_sensor per zone** (door / window / motion / smoke / etc., auto-classified
  from the panel's zone type), named from the panel ("Kitchen Door") and showing
  open/closed live. Each carries `bypassed`, `alarm`, `tamper`, `low_battery`, and
  `signal_level` as attributes.
* **System status sensors**: Alarm, Ready to arm, Low battery, AC power, Tamper, and
  (disabled by default) central-station/server comms, siren, and fire troubles.
  *Ready to arm* is reported by the panel when available; if your panel only exposes it
  via a status code it doesn't support, it's derived automatically — ready when no zone is
  open-and-unbypassed. The sensor lists the blocking zones in its `open_zones` attribute.
* **Services**:
  * `cove_alula.cancel_alarm` — send an alarm cancel to monitoring.
  * `cove_alula.confirm_alarm` — send an alarm confirm to monitoring.
  * `cove_alula.bypass_zone` — bypass/unbypass a zone by index
    (`{ "zone": 3, "bypass": true }`).
  * `cove_alula.force_arm` — arm when zones are open. `{ "mode": "away" }` bypasses any
    open zones then arms with your PIN (default, most reliable); `{ "mode": "away",
    "method": "native" }` uses the panel's built-in force-arm command instead. Bypasses
    clear on the next disarm.

State derives from live panel pushes: `disarmed`, `armed_home`, `armed_away`,
`armed_night`, `arming` (exit delay), `pending` (entry delay), `triggered` (in alarm).

---

## Verify it before relying on it

Bundled with the component is a standalone CLI (`custom_components/cove_alula/covealula.py`)
you can run on any machine with `python3` + `aiohttp` — no Home Assistant required. Use it
to confirm login and the correct arming-level numbers for **your** panel:

```bash
pip install aiohttp
python custom_components/cove_alula/covealula.py status   <user> '<password>'
python custom_components/cove_alula/covealula.py zones    <user> '<password>'
python custom_components/cove_alula/covealula.py names    <user> '<password>'
python custom_components/cove_alula/covealula.py disarm   <user> '<password>' <pin>
python custom_components/cove_alula/covealula.py arm_away <user> '<password>' <pin>
```

* `status` subscribes, pulls a full snapshot (name, firmware, zones), and prints every
  raw frame plus the parsed state and zone list.
* `zones` reads zone names/config/status and prints the parsed sensor list — use it to
  confirm the zone fields parse correctly on your panel.
* `names` prints your panel's arming-level labels so you can confirm which number means
  Stay vs Away vs Night.

### Arming-level mapping (important)

`armingLevelValue` is sent to the panel as: **1 = disarm**, 2 = first armed level
(usually *stay/home*), 3 = second armed level (usually *away*), 4+ = further/custom levels
(e.g. *night*). Level **0 is “unknown” and is not a valid command.** The meaning of each
*armed* level is configured **per panel** — only disarm (1) is universal. If `Arm Away`
or `Arm Home` lands on the wrong mode, run `names`, then adjust `LEVEL_STAY` / `LEVEL_AWAY`
/ `LEVEL_NIGHT` near the top of `covealula.py`.

---

## Troubleshooting

* **Entity shows `unknown` / no state.** The panel only streams state after the
  integration subscribes and pulls a snapshot — both happen automatically on setup. If it
  stays unknown, run the `status` CLI and look at the raw `<<` frames; that's the actual
  wire data.
* **`invalid_auth` at setup.** Wrong username/password. Remember the username may be your
  account number, not an email.
* **Login starts failing later with `invalid_client`.** The mobile client credentials
  embedded in the Cove app were rotated in a newer app version. They live in `covealula.py`
  (`CLIENT_ID` / `CLIENT_SECRET`) and can be re-extracted from a current app build.
* **Rate limited (HTTP 429).** Back off; don't loop auth/PIN attempts.

Enable debug logging to see frames in HA logs:

```yaml
logger:
  default: info
  logs:
    custom_components.cove_alula: debug
```

---

## How it works (short version)

* OAuth2 password grant against `https://api.alula.net/oauth/token` using the app's
  embedded mobile client id/secret + your username/password.
* Device discovery via the JSON:API REST endpoints (`/rest/v1/devices`).
* Live state + commands over `wss://api.alula.net/ws/v1`: subscribe to `device.status` +
  `device.helix`, pull a snapshot via `requestMfd` reads, and arm/disarm with
  `changeArmingLevelUsingCode` (PIN sent as a per-digit array).

Full protocol notes are in `cove_alula_protocol.md` (alongside this package).

---

## Support

This is a free, unofficial integration built in spare time. If it saved you some
work, you can say thanks with a coffee — entirely optional and always appreciated:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-FFDD00?logo=buymeacoffee&logoColor=black)](https://www.buymeacoffee.com/sam3gp8)

> [buymeacoffee.com/sam3gp8](https://www.buymeacoffee.com/sam3gp8)

---

## Disclaimer

Independent interoperability project. Not affiliated with, endorsed by, or supported by
Cove or Alula. Use at your own risk on your own account/equipment. A security system is
safety-critical — keep the official app installed and do not rely solely on this.
