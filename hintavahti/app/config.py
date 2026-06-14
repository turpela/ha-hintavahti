"""Configuration.

Priority for every setting: Home Assistant add-on options (/data/options.json)
-> environment variable -> built-in default. This lets the same code run both
as an HA add-on and as a plain Docker/standalone app.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

_OPTIONS_PATH = Path(os.environ.get("OPTIONS_PATH", "/data/options.json"))

try:
    _OPTIONS: dict = json.loads(_OPTIONS_PATH.read_text())
except Exception:  # noqa: BLE001 - file missing in standalone mode is normal
    _OPTIONS = {}


def _get(opt_key: str, env_key: str, default):
    if opt_key in _OPTIONS and _OPTIONS[opt_key] not in (None, ""):
        return _OPTIONS[opt_key]
    val = os.environ.get(env_key)
    return default if val is None or val == "" else val


def _as_bool(value, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _as_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# --- Storage ---
DATABASE_URL = _get("database_url", "DATABASE_URL", "sqlite:////data/pricetracker.db")

# --- Checking ---
CHECK_INTERVAL_HOURS = _as_float(_get("check_interval_hours", "CHECK_INTERVAL_HOURS", 6), 6)
REQUEST_DELAY_SECONDS = _as_float(_get("request_delay_seconds", "REQUEST_DELAY_SECONDS", 2), 2)
USER_AGENT = _get(
    "user_agent",
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
)
LOG_LEVEL = str(_get("log_level", "LOG_LEVEL", "INFO")).upper()

# Timezone used to display times in the UI. Defaults to the add-on/container
# TZ (which Home Assistant sets), falling back to Finnish time.
DISPLAY_TIMEZONE = str(_get("timezone", "TZ", "Europe/Helsinki")) or "Europe/Helsinki"

# --- Playwright (JS rendering) ---
PLAYWRIGHT_ENABLED = _as_bool(_get("playwright_enabled", "PLAYWRIGHT_ENABLED", True), True)
PLAYWRIGHT_TIMEOUT_MS = _as_int(_get("playwright_timeout_ms", "PLAYWRIGHT_TIMEOUT_MS", 30000), 30000)

# --- SMTP / email (optional) ---
SMTP_HOST = str(_get("smtp_host", "SMTP_HOST", ""))
SMTP_PORT = _as_int(_get("smtp_port", "SMTP_PORT", 587), 587)
SMTP_USER = str(_get("smtp_user", "SMTP_USER", ""))
SMTP_PASS = str(_get("smtp_pass", "SMTP_PASS", ""))
SMTP_FROM = str(_get("smtp_from", "SMTP_FROM", SMTP_USER or "hintavahti@localhost"))
SMTP_TLS = _as_bool(_get("smtp_tls", "SMTP_TLS", True), True)

# --- MQTT / Home Assistant sensors (optional) ---
MQTT_ENABLED = _as_bool(_get("mqtt_enabled", "MQTT_ENABLED", False), False)
# If MQTT_HOST is empty and we run as an add-on, we try the Supervisor MQTT service.
MQTT_HOST = str(_get("mqtt_host", "MQTT_HOST", ""))
MQTT_PORT = _as_int(_get("mqtt_port", "MQTT_PORT", 1883), 1883)
MQTT_USER = str(_get("mqtt_user", "MQTT_USER", ""))
MQTT_PASS = str(_get("mqtt_pass", "MQTT_PASS", ""))
MQTT_TLS = _as_bool(_get("mqtt_tls", "MQTT_TLS", False), False)
MQTT_DISCOVERY_PREFIX = str(_get("mqtt_discovery_prefix", "MQTT_DISCOVERY_PREFIX", "homeassistant"))

# Supervisor token is present only when running as an HA add-on.
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
