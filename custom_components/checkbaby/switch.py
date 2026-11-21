"""Switches for CheckBaby: the on/off settings."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import CheckBabyCoordinator
from .entity import CheckBabyEntity
from .models import CheckBabyConfigEntry

# Translation key and the Settings field it switches.
SWITCHES: tuple[tuple[str, str, EntityCategory | None], ...] = (
    ("monitoring", "armed", None),
    ("privacy_mode", "privacy", None),
    ("ai_assessment_enabled", "ai_enabled", EntityCategory.CONFIG),
    ("breathing_alert", "breathing_alert", EntityCategory.CONFIG),
    ("audio_relay_enabled", "vox_enabled", EntityCategory.CONFIG),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CheckBabyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the switches of one child."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(CheckBabySwitch(coordinator, *switch) for switch in SWITCHES)


class CheckBabySwitch(CheckBabyEntity, SwitchEntity):
    """One boolean setting."""

    def __init__(
        self, coordinator: CheckBabyCoordinator, key: str, field: str, category: EntityCategory | None
    ) -> None:
        """Bind the switch to a Settings field."""
        super().__init__(coordinator, key)
        self._field = field
        self._attr_entity_category = category

    @property
    def is_on(self) -> bool:
        """Return the setting."""
        return bool(getattr(self.coordinator.settings, self._field))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Switch the setting on."""
        await self.coordinator.async_set_setting(self._field, True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Switch the setting off."""
        await self.coordinator.async_set_setting(self._field, False)
        self.async_write_ha_state()
