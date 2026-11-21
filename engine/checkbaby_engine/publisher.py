"""MQTT publishing (paho-mqtt v2 API).

Topics, with ``<prefix>`` defaulting to ``checkbaby/engine``:

* ``<prefix>/<engine_id>/availability``: ``online`` / ``offline``, retained,
  ``offline`` is also the last will.
* ``<prefix>/<engine_id>/state``: JSON, not retained, about every two seconds
  and at once when the status changes.
"""

from __future__ import annotations

import json
import logging
import math
from typing import Any, Protocol

from .config import MqttConfig
from .signal import Result, Status

_LOGGER = logging.getLogger(__name__)

ONLINE = "online"
OFFLINE = "offline"


class MqttClient(Protocol):
    """The part of ``paho.mqtt.client.Client`` that is used here."""

    on_connect: Any

    def username_pw_set(self, username: str | None, password: str | None = None) -> None: ...
    def will_set(self, topic: str, payload: str, qos: int, retain: bool) -> None: ...
    def connect_async(self, host: str, port: int, keepalive: int) -> Any: ...
    def loop_start(self) -> Any: ...
    def loop_stop(self) -> Any: ...
    def publish(self, topic: str, payload: str, qos: int, retain: bool) -> Any: ...
    def disconnect(self) -> Any: ...


def _paho_client(client_id: str) -> MqttClient:
    from paho.mqtt.client import Client
    from paho.mqtt.enums import CallbackAPIVersion

    return Client(CallbackAPIVersion.VERSION2, client_id=client_id)


def state_payload(result: Result, ts: float) -> str:
    """The JSON for the state topic. ``rate`` is null unless the status is periodic."""
    rate = result.rate if result.status is Status.PERIODIC else None
    return json.dumps(
        {
            "status": result.status.value,
            "rate": None if rate is None or not math.isfinite(rate) else round(rate, 1),
            "confidence": _finite(result.confidence, 3, upper=1.0),
            "motion": _finite(result.motion, 3),
            "ts": round(ts, 3),
        },
        allow_nan=False,
    )


def _finite(value: float, digits: int, upper: float = math.inf) -> float:
    return round(min(max(value, 0.0), upper), digits) if math.isfinite(value) else 0.0


class Publisher:
    def __init__(self, config: MqttConfig, engine_id: str, client: MqttClient | None = None) -> None:
        self._config = config
        base = f"{config.topic_prefix}/{engine_id}"
        self.availability_topic = f"{base}/availability"
        self.state_topic = f"{base}/state"
        self._client = client or _paho_client(f"checkbaby-engine-{engine_id}")
        self._last_status: Status | None = None
        self._last_publish: float | None = None

    def start(self) -> None:
        """Connect in the background; paho reconnects on its own after a loss."""
        client, cfg = self._client, self._config
        if cfg.username:
            client.username_pw_set(cfg.username, cfg.password or None)
        client.will_set(self.availability_topic, OFFLINE, qos=1, retain=True)
        client.on_connect = self._on_connect
        client.connect_async(cfg.host, cfg.port, keepalive=30)
        client.loop_start()

    def _on_connect(self, client: Any, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
        if getattr(reason_code, "is_failure", False):
            _LOGGER.warning("MQTT connection refused: %s", reason_code)
            return
        _LOGGER.info("MQTT connected to %s:%s", self._config.host, self._config.port)
        self._client.publish(self.availability_topic, ONLINE, qos=1, retain=True)

    def update(self, result: Result, now: float) -> bool:
        """Publish the state if the status changed or the interval has passed."""
        changed = result.status is not self._last_status
        due = self._last_publish is None or now - self._last_publish >= self._config.publish_interval_s
        if not (changed or due):
            return False
        self._client.publish(self.state_topic, state_payload(result, now), qos=0, retain=False)
        self._last_status, self._last_publish = result.status, now
        return True

    def stop(self) -> None:
        """Announce ``offline`` (a clean disconnect does not trigger the last will)."""
        info = self._client.publish(self.availability_topic, OFFLINE, qos=1, retain=True)
        try:
            info.wait_for_publish(timeout=2.0)
        except (AttributeError, RuntimeError, ValueError):
            pass  # not connected: the broker's last will has already said offline
        self._client.disconnect()
        self._client.loop_stop()
