"""Sends what the monitor decided: pushes, the local alarm channel, clears."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant

from .alerts import Notification
from .const import (
    CONF_BABYSITTER_SERVICE,
    CONF_DASHBOARD_PATH,
    CONF_LOCAL_ALARM,
    CONF_NOTIFY_SERVICES,
    DEFAULT_DASHBOARD_PATH,
)
from .push import build_clear, build_push
from .texts import alert_title
from .types import ON_DUTY_ALL, AlertLevel, Audience, Mode, Stage

if TYPE_CHECKING:
    from .coordinator import CheckBabyCoordinator

_LOGGER = logging.getLogger(__name__)

_PUSH_STAGES = (Stage.FIRST, Stage.UPGRADE, Stage.REPEAT, Stage.ESCALATE)


class Notifier:
    """Turns notifications into Home Assistant service calls."""

    def __init__(self, hass: HomeAssistant, coordinator: CheckBabyCoordinator) -> None:
        """Bind to one child."""
        self._hass = hass
        self._coordinator = coordinator
        # Remembered across restarts, so that an alarm left on can still be switched off.
        self.local_on = False

    @property
    def _options(self) -> dict[str, Any]:
        return dict(self._coordinator.config_entry.options)

    def all_services(self) -> list[str]:
        """Every configured notify service, plus the babysitter's in babysitter mode."""
        services = list(self._options.get(CONF_NOTIFY_SERVICES, []))
        babysitter = self._options.get(CONF_BABYSITTER_SERVICE)
        if babysitter and self._coordinator.settings.mode is Mode.BABYSITTER and babysitter not in services:
            services.append(babysitter)
        return services

    def services_for(self, audience: Audience) -> list[str]:
        """The notify services an audience maps to."""
        services = self.all_services()
        on_duty = self._coordinator.settings.on_duty
        if audience is Audience.ON_DUTY and on_duty != ON_DUTY_ALL and on_duty in services:
            return [on_duty]
        return services

    def missing_services(self) -> list[str]:
        """Configured notify services that Home Assistant does not have."""
        return [name for name in self.all_services() if not self._hass.services.has_service("notify", name)]

    def has_target(self) -> bool:
        """True if an alert can reach anyone at all."""
        return bool(self.all_services() or self._options.get(CONF_LOCAL_ALARM))

    async def async_handle(self, note: Notification) -> None:
        """Carry out one notification."""
        if note.stage in _PUSH_STAGES:
            await self._async_push(note)
        elif note.stage is Stage.LOCAL:
            await self._async_local(True)
        else:
            entry_id = self._coordinator.config_entry.entry_id
            await self._async_notify(self.all_services(), build_clear(entry_id, note.kind))
            if not self._coordinator.monitor.alerts.needs_attention():
                await self._async_local(False)

    async def _async_push(self, note: Notification) -> None:
        coordinator = self._coordinator
        place = coordinator.active_place
        payload = build_push(
            language=self._hass.config.language,
            child=coordinator.child_name,
            entry_id=coordinator.config_entry.entry_id,
            kind=note.kind,
            level=note.level,
            detail=note.detail,
            camera_entity=place.camera_entity if place else None,
            dashboard_path=self._options.get(CONF_DASHBOARD_PATH, DEFAULT_DASHBOARD_PATH),
        )
        await self._async_notify(self.services_for(note.audience), payload)

    async def async_send_text(self, message: str, *, level: AlertLevel = AlertLevel.WARNING) -> None:
        """Send a plain message, e.g. a quick check or the night report, to who is on duty."""
        title = alert_title(self._hass.config.language, self._coordinator.child_name, level)
        await self._async_notify(self.services_for(Audience.ON_DUTY), {"title": title, "message": message})

    async def _async_notify(self, services: list[str], payload: dict[str, Any]) -> None:
        for name in services:
            if not self._hass.services.has_service("notify", name):
                _LOGGER.warning("Notify service notify.%s does not exist", name)
                continue
            try:
                await self._hass.services.async_call("notify", name, dict(payload), blocking=True)
            except Exception:  # noqa: BLE001 - one failing phone must not stop the others
                _LOGGER.exception("Sending to notify.%s failed", name)

    async def _async_local(self, on: bool) -> None:
        entities = list(self._options.get(CONF_LOCAL_ALARM, []))
        if not entities or on == self.local_on:
            return
        self.local_on = on
        try:
            await self._hass.services.async_call(
                "homeassistant", "turn_on" if on else "turn_off", {"entity_id": entities}, blocking=True
            )
        except Exception:  # noqa: BLE001 - the push path must go on regardless
            _LOGGER.exception("Switching the local alarm channel failed")
