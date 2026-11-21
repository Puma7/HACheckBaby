"""A switch that stands in for the siren in the parents' bedroom."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .entity import LabEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the siren."""
    async_add_entities([LabSiren(hass, "siren", "Siren")])


class LabSiren(LabEntity, SwitchEntity):
    """Records when it was switched."""

    _attr_is_on = False

    def _switch(self, on: bool) -> None:
        self._attr_is_on = on
        self.lab.siren_calls.append((dt_util.utcnow().timestamp(), on))
        self.lab.changed()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Sound."""
        self._switch(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Be quiet."""
        self._switch(False)
