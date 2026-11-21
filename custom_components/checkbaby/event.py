"""Event entity for CheckBaby: fires when an alert notifies or gets worse."""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .alerts import Notification
from .coordinator import CheckBabyCoordinator
from .entity import CheckBabyEntity
from .models import CheckBabyConfigEntry
from .types import AlertKind


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CheckBabyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the alert event of one child."""
    async_add_entities([AlertEvent(entry.runtime_data.coordinator)])


class AlertEvent(CheckBabyEntity, EventEntity):
    """One event per alert, for automations."""

    _attr_event_types = [kind.value for kind in AlertKind]

    def __init__(self, coordinator: CheckBabyCoordinator) -> None:
        """Bind to one child."""
        super().__init__(coordinator, "alert")

    async def async_added_to_hass(self) -> None:
        """Start listening for alerts."""
        await super().async_added_to_hass()
        listeners = self.coordinator.alert_listeners
        listeners.append(self._handle_alert)
        self.async_on_remove(lambda: listeners.remove(self._handle_alert))

    @callback
    def _handle_alert(self, note: Notification) -> None:
        self._trigger_event(note.kind.value, {"level": note.level.name.lower(), **note.detail})
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Snapshots do not change the event state."""
