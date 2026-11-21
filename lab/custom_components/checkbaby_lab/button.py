"""A button that stands in for the heartbeat input of a dead-man buzzer."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import LabEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the heartbeat button."""
    async_add_entities([LabHeartbeat(hass, "deadman", "Dead-man heartbeat")])


class LabHeartbeat(LabEntity, ButtonEntity):
    """Counts how often CheckBaby says it is alive."""

    async def async_press(self) -> None:
        """Count one heartbeat."""
        self.lab.heartbeats += 1
        self.lab.changed()
