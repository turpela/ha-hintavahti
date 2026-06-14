"""Publish tracked products to Home Assistant as MQTT sensors.

Each product becomes a sensor (e.g. sensor.hintavahti_<id>) grouped under one
"Hintavahti" device, with the price as state and details as attributes. Uses
MQTT discovery so entities appear automatically.

If MQTT is disabled, paho-mqtt is missing, or no broker can be resolved, every
function is a safe no-op. When running as an HA add-on with no explicit broker
configured, the broker is auto-discovered from the Supervisor MQTT service.
"""
from __future__ import annotations

import json
import logging
import threading

from . import config
from .database import iso_utc

log = logging.getLogger("hintavahti.mqtt")

_client = None
_lock = threading.Lock()
_resolved: dict | None = None
_AVAILABILITY_TOPIC = "hintavahti/status"


def _resolve_broker() -> dict | None:
    """Return broker settings from config, or from the Supervisor service."""
    if config.MQTT_HOST:
        return {
            "host": config.MQTT_HOST,
            "port": config.MQTT_PORT,
            "username": config.MQTT_USER,
            "password": config.MQTT_PASS,
            "ssl": config.MQTT_TLS,
        }
    if config.SUPERVISOR_TOKEN:
        try:
            import httpx
            resp = httpx.get(
                "http://supervisor/services/mqtt",
                headers={"Authorization": f"Bearer {config.SUPERVISOR_TOKEN}"},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
            if data.get("host"):
                log.info("MQTT-broker haettu Supervisorilta: %s", data["host"])
                return {
                    "host": data["host"],
                    "port": int(data.get("port", 1883)),
                    "username": data.get("username", ""),
                    "password": data.get("password", ""),
                    "ssl": bool(data.get("ssl", False)),
                }
        except Exception as exc:  # noqa: BLE001
            log.warning("MQTT-brokerin haku Supervisorilta epäonnistui: %s", exc)
    return None


def _get_client():
    """Return a connected paho client, or None if MQTT is unavailable."""
    global _client, _resolved
    if not config.MQTT_ENABLED:
        return None
    if _client is not None:
        return _client
    with _lock:
        if _client is not None:
            return _client
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            log.warning("paho-mqtt puuttuu — MQTT pois käytöstä.")
            return None

        broker = _resolve_broker()
        if not broker:
            log.warning("MQTT käytössä mutta brokeria ei löytynyt.")
            return None
        _resolved = broker

        try:
            client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id="hintavahti",
            )
        except (AttributeError, TypeError):
            client = mqtt.Client(client_id="hintavahti")  # paho < 2.0

        if broker["username"]:
            client.username_pw_set(broker["username"], broker["password"])
        if broker["ssl"]:
            client.tls_set()
        client.will_set(_AVAILABILITY_TOPIC, "offline", retain=True)

        try:
            client.connect(broker["host"], broker["port"], keepalive=60)
            client.loop_start()
            client.publish(_AVAILABILITY_TOPIC, "online", retain=True)
            _client = client
            log.info("Yhteys MQTT-brokeriin %s muodostettu.", broker["host"])
        except Exception as exc:  # noqa: BLE001
            log.error("MQTT-yhteys epäonnistui: %s", exc)
            return None
    return _client


def _discovery_topic(product_id: int) -> str:
    return f"{config.MQTT_DISCOVERY_PREFIX}/sensor/hintavahti/{product_id}/config"


def _state_topic(product_id: int) -> str:
    return f"hintavahti/{product_id}/state"


def _attr_topic(product_id: int) -> str:
    return f"hintavahti/{product_id}/attributes"


def publish_product(product) -> None:
    """Publish (or refresh) discovery config, state and attributes."""
    client = _get_client()
    if client is None:
        return

    config_payload = {
        "name": product.name,
        "unique_id": f"hintavahti_{product.id}",
        "object_id": f"hintavahti_{product.id}",
        "state_topic": _state_topic(product.id),
        "json_attributes_topic": _attr_topic(product.id),
        "availability_topic": _AVAILABILITY_TOPIC,
        "unit_of_measurement": "€",
        "state_class": "measurement",
        "suggested_display_precision": 2,
        "icon": "mdi:tag-arrow-down",
        "device": {
            "identifiers": ["hintavahti"],
            "name": "Hintavahti",
            "manufacturer": "Hintavahti",
            "model": "Price tracker",
        },
    }
    client.publish(_discovery_topic(product.id), json.dumps(config_payload), retain=True)

    if product.last_price is not None:
        client.publish(_state_topic(product.id), f"{product.last_price:.2f}", retain=True)

    attributes = {
        "url": product.url,
        "lowest_price": product.lowest_price,
        "target_price": product.target_price,
        "last_checked": iso_utc(product.last_checked),
        "error": product.last_error or "",
    }
    client.publish(_attr_topic(product.id), json.dumps(attributes), retain=True)


def remove_product(product_id: int) -> None:
    """Remove a product's sensor by clearing its discovery topic."""
    client = _get_client()
    if client is None:
        return
    client.publish(_discovery_topic(product_id), "", retain=True)
    client.publish(_state_topic(product_id), "", retain=True)
    client.publish(_attr_topic(product_id), "", retain=True)


def publish_all(products) -> None:
    for product in products:
        publish_product(product)
