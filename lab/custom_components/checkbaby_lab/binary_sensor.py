"""Simulated door contact, bed presence, smoke detector and internet connectivity."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import LabEntity

BINARY_SENSORS = (("door", "Door"), ("presence", "In bed"), ("smoke", "Smoke"), ("internet", "Internet"))


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the binary sensors."""
    async_add_entities(LabBinarySensor(hass, key, name) for key, name in BINARY_SENSORS)


class LabBinarySensor(LabEntity, BinarySensorEntity):
    """A yes/no value a scenario sets with the action checkbaby_lab.set."""

    @property
    def is_on(self) -> bool | None:
        """Return the simulated value; None shows as unknown."""
        return self.lab.values.get(self._key)
