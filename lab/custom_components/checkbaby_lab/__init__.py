"""CheckBaby Lab: simulated phones, sensors, camera and AI for trying CheckBaby out.

Everything here stands in for hardware. It is never installed with CheckBaby;
it only exists so that a real Home Assistant can run the real integration
without a camera, a phone or a radar.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .const import DEFAULTS, DOMAIN, GOOD_ANSWER, PHONES

PLATFORMS = [
    Platform.AI_TASK,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CAMERA,
    Platform.MEDIA_PLAYER,
    Platform.SENSOR,
    Platform.SWITCH,
]


@dataclass
class Lab:
    """Shared state of the simulated world."""

    values: dict[str, Any] = field(default_factory=lambda: dict(DEFAULTS))
    pushes: list[dict[str, Any]] = field(default_factory=list)
    ai_answer: Any = field(default_factory=lambda: dict(GOOD_ANSWER))
    ai_calls: list[dict[str, Any]] = field(default_factory=list)
    siren_calls: list[tuple[float, bool]] = field(default_factory=list)
    heartbeats: int = 0
    media: list[dict[str, Any]] = field(default_factory=list)
    listeners: list[Callable[[], None]] = field(default_factory=list)

    @callback
    def changed(self) -> None:
        """Tell the entities that something changed."""
        for listener in list(self.listeners):
            listener()

    def real_pushes(self, phone: str | None = None) -> list[dict[str, Any]]:
        """Pushes that show on a phone, without the clear messages."""
        return [
            push
            for push in self.pushes
            if push["message"] != "clear_notification" and (phone is None or push["phone"] == phone)
        ]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Create the single lab entry when `checkbaby_lab:` is in configuration.yaml."""
    if DOMAIN in config and not hass.config_entries.async_entries(DOMAIN):
        hass.async_create_task(
            hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_IMPORT}, data={})
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the simulated devices."""
    lab = hass.data[DOMAIN] = Lab()

    def phone(name: str) -> Callable[[ServiceCall], None]:
        @callback
        def _receive(call: ServiceCall) -> None:
            lab.pushes.append(
                {
                    "at": dt_util.utcnow().timestamp(),
                    "phone": name,
                    "title": call.data.get("title"),
                    "message": call.data.get("message"),
                    "data": dict(call.data.get("data") or {}),
                }
            )
            lab.changed()

        return _receive

    for name in PHONES:
        hass.services.async_register("notify", name, phone(name))

    @callback
    def _set(call: ServiceCall) -> None:
        lab.values.update(call.data)
        lab.changed()

    @callback
    def _ai(call: ServiceCall) -> None:
        mode = call.data.get("mode", "answer")
        lab.ai_answer = mode if mode != "answer" else {**GOOD_ANSWER, **call.data.get("fields", {})}

    @callback
    def _tap(call: ServiceCall) -> None:
        """A parent taps a button on the notification."""
        action = {"seen": "CHECKBABY_ACK", "quiet": "CHECKBABY_SNOOZE"}[call.data["button"]]
        hass.bus.async_fire("mobile_app_notification_action", {"action": f"{action}_{call.data['entry_id']}"})

    @callback
    def _reset(call: ServiceCall) -> None:
        lab.pushes.clear()
        lab.ai_calls.clear()
        lab.siren_calls.clear()
        lab.media.clear()
        lab.changed()

    hass.services.async_register(DOMAIN, "set", _set)
    hass.services.async_register(DOMAIN, "ai", _ai)
    hass.services.async_register(DOMAIN, "tap", _tap)
    hass.services.async_register(DOMAIN, "reset", _reset)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove the simulated devices."""
    for name in PHONES:
        hass.services.async_remove("notify", name)
    for service in ("set", "ai", "tap", "reset"):
        hass.services.async_remove(DOMAIN, service)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
