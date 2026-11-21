"""Numbers for CheckBaby: the adjustable thresholds."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import CheckBabyCoordinator
from .entity import CheckBabyEntity
from .models import CheckBabyConfigEntry


@dataclass(frozen=True, kw_only=True)
class CheckBabyNumberDescription(NumberEntityDescription):
    """A threshold; the key is the Settings field."""


NUMBERS: tuple[CheckBabyNumberDescription, ...] = (
    CheckBabyNumberDescription(
        key="cry_warning_s", native_min_value=5, native_max_value=120, native_step=1,
        native_unit_of_measurement=UnitOfTime.SECONDS,
    ),
    CheckBabyNumberDescription(
        key="cry_critical_s", native_min_value=60, native_max_value=900, native_step=10,
        native_unit_of_measurement=UnitOfTime.SECONDS,
    ),
    CheckBabyNumberDescription(
        key="noise_margin_db", native_min_value=3, native_max_value=40, native_step=1,
        native_unit_of_measurement="dB",
    ),
    # Newborns pause for up to about ten seconds as part of normal breathing,
    # so the delay cannot be set below twenty.
    CheckBabyNumberDescription(
        key="no_breathing_s", native_min_value=20, native_max_value=60, native_step=1,
        native_unit_of_measurement=UnitOfTime.SECONDS,
    ),
    CheckBabyNumberDescription(
        key="ai_interval_min", native_min_value=2, native_max_value=60, native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
    ),
    CheckBabyNumberDescription(
        key="temp_min", native_min_value=10, native_max_value=22, native_step=0.5,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE,
    ),
    CheckBabyNumberDescription(
        key="temp_max", native_min_value=18, native_max_value=30, native_step=0.5,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE,
    ),
)  # fmt: skip


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CheckBabyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the numbers of one child."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(CheckBabyNumber(coordinator, description) for description in NUMBERS)


class CheckBabyNumber(CheckBabyEntity, NumberEntity):
    """One numeric setting."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: CheckBabyCoordinator, description: CheckBabyNumberDescription) -> None:
        """Bind the number to a Settings field."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float:
        """Return the setting."""
        return float(getattr(self.coordinator.settings, self.entity_description.key))

    async def async_set_native_value(self, value: float) -> None:
        """Change the setting."""
        await self.coordinator.async_set_setting(self.entity_description.key, float(value))
        self.async_write_ha_state()
