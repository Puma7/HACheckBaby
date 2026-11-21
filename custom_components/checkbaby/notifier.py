"""Sends what the monitor decided: pushes, notifications in Home Assistant, the local alarm."""

from __future__ import annotations

from collections.abc import Coroutine
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components import persistent_notification
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from .alerts import Notification
from .const import (
    CONF_BABYSITTER_SERVICE,
    CONF_DASHBOARD_PATH,
    CONF_LOCAL_ALARM,
    CONF_NOTIFY_SERVICES,
    DEFAULT_DASHBOARD_PATH,
)
from .push import build_clear, build_push, notification_tag
from .texts import alert_message, alert_title, delivery_report
from .types import ON_DUTY_ALL, AlertKind, AlertLevel, Audience, Mode, Stage

if TYPE_CHECKING:
    from .coordinator import CheckBabyCoordinator

_LOGGER = logging.getLogger(__name__)

_PUSH_STAGES = (Stage.FIRST, Stage.UPGRADE, Stage.REPEAT, Stage.ESCALATE)


def as_list(value: Any) -> list[str]:
    """Options that may hold one name or several, as a list."""
    if not value:
        return []
    return [str(value)] if isinstance(value, str) else [str(item) for item in value]


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
        """Every configured notify service, plus the babysitters' in babysitter mode."""
        services = as_list(self._options.get(CONF_NOTIFY_SERVICES))
        if self._coordinator.settings.mode is Mode.BABYSITTER:
            services += [name for name in as_list(self._options.get(CONF_BABYSITTER_SERVICE)) if name not in services]
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

    def local_alarm_unavailable(self) -> list[str]:
        """Local alarm entities that are missing or unavailable: they would stay silent."""
        unavailable = []
        for entity_id in as_list(self._options.get(CONF_LOCAL_ALARM)):
            state = self._hass.states.get(entity_id)
            if state is None or state.state == STATE_UNAVAILABLE:
                unavailable.append(entity_id)
        return unavailable

    async def async_handle(self, note: Notification) -> None:
        """Carry out one notification."""
        entry_id = self._coordinator.config_entry.entry_id
        tag = notification_tag(entry_id, note.kind)
        if note.stage in _PUSH_STAGES:
            sent, failed = await self._async_push(note)
            if note.stage is not Stage.REPEAT:
                # Also where it can be seen without a phone: the notifications of Home Assistant.
                language = self._hass.config.language
                child = self._coordinator.child_name
                title = alert_title(language, child, note.level)
                persistent_notification.async_create(
                    self._hass,
                    alert_message(language, child, note.kind, note.level, note.detail),
                    title=title,
                    notification_id=tag,
                )
                if note.kind is AlertKind.TEST:
                    # A test is there to find out what works, so it says where it went.
                    # Its own notification: it stays when the test alert is answered.
                    report = delivery_report(
                        language,
                        sent=[f"notify.{name}" for name in sent],
                        failed=[f"notify.{name}" for name in failed],
                        local=as_list(self._options.get(CONF_LOCAL_ALARM)),
                        local_down=self.local_alarm_unavailable(),
                    )
                    persistent_notification.async_create(
                        self._hass, report, title=title, notification_id=f"{tag}_delivery"
                    )
        elif note.stage is not Stage.LOCAL:
            await self._async_notify(self.all_services(), build_clear(entry_id, note.kind))
            persistent_notification.async_dismiss(self._hass, tag)

    async def _async_push(self, note: Notification) -> tuple[list[str], list[str]]:
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
        services = self.services_for(note.audience)
        _LOGGER.debug(
            "Alert %s (%s, %s) goes to %s", note.kind.value, note.level.name.lower(), note.stage.value, services or "no phone"
        )
        return await self._async_notify(services, payload)

    async def async_send_text(self, message: str, *, topic: str, level: AlertLevel = AlertLevel.INFO) -> None:
        """Show a result, e.g. a quick check or the night report.

        It goes to who is on duty and into Home Assistant's own notifications,
        so that pressing a button always shows something, also without a phone.
        """
        title = alert_title(self._hass.config.language, self._coordinator.child_name, level)
        tag = f"checkbaby_{self._coordinator.config_entry.entry_id}_{topic}"
        persistent_notification.async_create(self._hass, message, title=title, notification_id=tag)
        # The tag lets a newer result replace the older one on the phone.
        payload = {"title": title, "message": message, "data": {"tag": tag}}
        await self._async_notify(self.services_for(Audience.ON_DUTY), payload)

    async def _async_notify(self, services: list[str], payload: dict[str, Any]) -> tuple[list[str], list[str]]:
        """Send to each service; return which accepted the message and which did not."""
        sent: list[str] = []
        failed: list[str] = []
        for name in services:
            if not self._hass.services.has_service("notify", name):
                _LOGGER.warning("Notify service notify.%s does not exist", name)
                failed.append(name)
                continue
            try:
                await self._hass.services.async_call("notify", name, dict(payload), blocking=True)
            except Exception:  # noqa: BLE001 - one failing phone must not stop the others
                _LOGGER.exception("Sending to notify.%s failed", name)
                failed.append(name)
            else:
                sent.append(name)
        return sent, failed

    def local_change(self, wanted: bool) -> Coroutine[Any, Any, None] | None:
        """Return the call that brings the local alarm in line with the alerts, if one is needed.

        The channel follows the state of the alerts, not single events, so it
        cannot be left on by an alert that ended in an unusual way.
        """
        if wanted == self.local_on or not self._options.get(CONF_LOCAL_ALARM):
            return None
        self.local_on = wanted
        return self._async_local(wanted)

    async def _async_local(self, on: bool) -> None:
        entities = as_list(self._options.get(CONF_LOCAL_ALARM))
        _LOGGER.debug("Local alarm %s: %s", "on" if on else "off", entities)
        try:
            await self._hass.services.async_call(
                "homeassistant", "turn_on" if on else "turn_off", {"entity_id": entities}, blocking=True
            )
        except Exception:  # noqa: BLE001 - the push path must go on regardless
            _LOGGER.exception("Switching the local alarm channel failed")
