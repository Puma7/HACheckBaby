"""Sensors for CheckBaby."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .models import CheckBabyConfigEntry
from .profiles import AgeProfile, profile_for


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CheckBabyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the sensors of one child."""
    async_add_entities([AgeProfileSensor(entry)])


class AgeProfileSensor(SensorEntity):
    """The age profile that selects the child's default thresholds."""

    _attr_has_entity_name = True
    _attr_translation_key = "age_profile"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [profile.value for profile in AgeProfile]
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False

    def __init__(self, entry: CheckBabyConfigEntry) -> None:
        """Bind the sensor to one child."""
        self._birth_date = entry.runtime_data.birth_date
        self._attr_unique_id = f"{entry.entry_id}_age_profile"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.runtime_data.child_name,
            manufacturer="CheckBaby",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> str:
        """Return the profile for today's date."""
        return profile_for(self._birth_date, dt_util.now().date()).value

    async def async_added_to_hass(self) -> None:
        """Re-evaluate shortly after local midnight, when the age changes."""
        self.async_on_remove(
            async_track_time_change(self.hass, self._handle_new_day, hour=0, minute=0, second=10)
        )

    @callback
    def _handle_new_day(self, now: datetime) -> None:
        self.async_write_ha_state()
