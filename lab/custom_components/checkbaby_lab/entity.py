"""Base entity of the lab simulator."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from . import Lab
from .const import DOMAIN


class LabEntity(Entity):
    """An entity that mirrors the simulated world."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, key: str, name: str) -> None:
        """Name the entity; the entity id becomes <platform>.lab_<key>."""
        self.lab: Lab = hass.data[DOMAIN]
        self._key = key
        self._attr_unique_id = f"checkbaby_lab_{key}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "lab")}, name="Lab", manufacturer="CheckBaby", entry_type=DeviceEntryType.SERVICE
        )

    async def async_added_to_hass(self) -> None:
        """Follow changes of the simulated world."""
        self.lab.listeners.append(self.async_write_ha_state)
        self.async_on_remove(lambda: self.lab.listeners.remove(self.async_write_ha_state))
