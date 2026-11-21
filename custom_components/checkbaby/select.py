"""Selects for CheckBaby: mode, sensitivity, who is on duty, active sleep place."""

from __future__ import annotations

from enum import StrEnum

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_NOTIFY_SERVICES
from .coordinator import CheckBabyCoordinator
from .entity import CheckBabyEntity
from .models import CheckBabyConfigEntry
from .types import ON_DUTY_ALL, Mode, Sensitivity, VitalFusion

ENUM_SELECTS: tuple[tuple[str, type[StrEnum], EntityCategory | None], ...] = (
    ("mode", Mode, None),
    ("sensitivity", Sensitivity, EntityCategory.CONFIG),
    ("vital_fusion", VitalFusion, EntityCategory.CONFIG),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CheckBabyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the selects of one child."""
    coordinator = entry.runtime_data.coordinator
    entities: list[SelectEntity] = [EnumSelect(coordinator, *select) for select in ENUM_SELECTS]
    entities.append(OnDutySelect(coordinator))
    entities.append(SleepPlaceSelect(coordinator))
    async_add_entities(entities)


class EnumSelect(CheckBabyEntity, SelectEntity):
    """A setting with a fixed list of choices."""

    def __init__(
        self,
        coordinator: CheckBabyCoordinator,
        field: str,
        enum: type[StrEnum],
        category: EntityCategory | None,
    ) -> None:
        """Bind the select to a Settings field."""
        super().__init__(coordinator, field)
        self._field = field
        self._enum = enum
        self._attr_options = [member.value for member in enum]
        self._attr_entity_category = category

    @property
    def current_option(self) -> str:
        """Return the setting."""
        return str(getattr(self.coordinator.settings, self._field).value)

    async def async_select_option(self, option: str) -> None:
        """Change the setting."""
        await self.coordinator.async_set_setting(self._field, self._enum(option))
        self.async_write_ha_state()


class OnDutySelect(CheckBabyEntity, SelectEntity):
    """Who gets warnings first. Critical alerts always reach everyone."""

    def __init__(self, coordinator: CheckBabyCoordinator) -> None:
        """Offer every notify target plus "all"."""
        super().__init__(coordinator, "on_duty")

    @property
    def options(self) -> list[str]:
        """Return "all" and the configured notify services."""
        return [ON_DUTY_ALL, *self.coordinator.config_entry.options.get(CONF_NOTIFY_SERVICES, [])]

    @property
    def current_option(self) -> str:
        """Return who is on duty; "all" if the stored target no longer exists."""
        on_duty = self.coordinator.settings.on_duty
        return on_duty if on_duty in self.options else ON_DUTY_ALL

    async def async_select_option(self, option: str) -> None:
        """Change who is on duty."""
        await self.coordinator.async_set_setting("on_duty", option)
        self.async_write_ha_state()


class SleepPlaceSelect(CheckBabyEntity, SelectEntity):
    """Which sleep place is being monitored."""

    def __init__(self, coordinator: CheckBabyCoordinator) -> None:
        """Offer the configured sleep places by name."""
        super().__init__(coordinator, "active_place")

    @property
    def options(self) -> list[str]:
        """Return the names of the sleep places."""
        return [place.name for place in self.coordinator.places.values()]

    @property
    def current_option(self) -> str | None:
        """Return the name of the active sleep place."""
        place = self.coordinator.active_place
        return place.name if place else None

    async def async_select_option(self, option: str) -> None:
        """Monitor a different sleep place."""
        for place in self.coordinator.places.values():
            if place.name == option:
                await self.coordinator.async_set_setting("active_place", place.place_id)
                break
        self.async_write_ha_state()
