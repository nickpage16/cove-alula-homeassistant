"""Constants for the Cove (Alula) Alarm integration."""

DOMAIN = "cove_alula"
PLATFORMS = ["alarm_control_panel", "binary_sensor"]

CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_PIN = "pin"
CONF_TOKEN = "token"  # persisted CoveToken dict (so restarts don't re-login)

# Fallback REST poll interval; live updates arrive over the websocket.
POLL_INTERVAL_SECONDS = 30

# Services
SERVICE_CANCEL_ALARM = "cancel_alarm"
SERVICE_CONFIRM_ALARM = "confirm_alarm"
SERVICE_BYPASS_ZONE = "bypass_zone"
SERVICE_FORCE_ARM = "force_arm"
ATTR_ZONE = "zone"
ATTR_BYPASS = "bypass"
ATTR_MODE = "mode"
ATTR_METHOD = "method"
