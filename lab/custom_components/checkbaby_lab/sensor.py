"""Simulated radar and room sensors, and a counter of received pushes."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import LabEntity

SENSORS = (
    ("breath_rate", "Breath rate", "/min", None),
    ("heart_rate", "Heart rate", "bpm", None),
    ("temperature", "Temperature", "°C", SensorDeviceClass.TEMPERATURE),
    ("humidity", "Humidity", "%", SensorDeviceClass.HUMIDITY),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the sensors."""
    entities: list[SensorEntity] = [LabSensor(hass, *sensor) for sensor in SENSORS]
    entities.append(PushCounter(hass))
    async_add_entities(entities)


class LabSensor(LabEntity, SensorEntity):
    """A value a scenario sets with the action checkbaby_lab.set."""

    def __init__(
        self, hass: HomeAssistant, key: str, name: str, unit: str, device_class: SensorDeviceClass | None
    ) -> None:
        """Bind to one simulated value."""
        super().__init__(hass, key, name)
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class

    @property
    def native_value(self) -> float | None:
        """Return the simulated value; None shows as unknown."""
        return self.lab.values.get(self._key)

    @property
    def force_update(self) -> bool:
        """Report again even if the value did not change, like a live sensor."""
        return True


class PushCounter(LabEntity, SensorEntity):
    """How many notifications the simulated phones received, with the latest ones."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Count the pushes."""
        super().__init__(hass, "pushes", "Pushes received")

    @property
    def native_value(self) -> int:
        """Return the number of pushes that show on a phone."""
        return len(self.lab.real_pushes())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the last few pushes."""
        return {
            "latest": [
                {"phone": push["phone"], "title": push["title"], "message": push["message"]}
                for push in self.lab.real_pushes()[-8:]
            ],
            "siren_switches": len(self.lab.siren_calls),
            "heartbeats": self.lab.heartbeats,
            "ai_calls": len(self.lab.ai_calls),
        }
