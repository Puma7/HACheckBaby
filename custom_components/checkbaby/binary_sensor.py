"""Binary sensors for CheckBaby."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import CheckBabyCoordinator
from .entity import CheckBabyEntity
from .models import CheckBabyConfigEntry
from .monitor import Snapshot
from .types import ChildState


@dataclass(frozen=True, kw_only=True)
class CheckBabyBinarySensorDescription(BinarySensorEntityDescription):
    """A binary sensor and how its value is read. None means unknown."""

    is_on_fn: Callable[[Snapshot, CheckBabyCoordinator], bool | None]


def _quiet_time(snapshot: Snapshot, coordinator: CheckBabyCoordinator) -> bool:
    settings = coordinator.settings
    asleep = snapshot.state in (ChildState.ASLEEP, ChildState.RESTLESS)
    return settings.armed and not settings.privacy and asleep


BINARY_SENSORS: tuple[CheckBabyBinarySensorDescription, ...] = (
    CheckBabyBinarySensorDescription(
        key="crying", device_class=BinarySensorDeviceClass.SOUND, is_on_fn=lambda snap, _: snap.crying
    ),
    CheckBabyBinarySensorDescription(
        key="motion", device_class=BinarySensorDeviceClass.MOTION, is_on_fn=lambda snap, _: snap.motion
    ),
    CheckBabyBinarySensorDescription(
        key="in_bed", device_class=BinarySensorDeviceClass.OCCUPANCY, is_on_fn=lambda snap, _: snap.in_bed
    ),
    CheckBabyBinarySensorDescription(key="attended", is_on_fn=lambda snap, _: snap.attended),
    CheckBabyBinarySensorDescription(key="breathing_movement", is_on_fn=lambda snap, _: snap.breathing),
    CheckBabyBinarySensorDescription(
        key="alert_active",
        device_class=BinarySensorDeviceClass.SAFETY,
        is_on_fn=lambda snap, _: snap.needs_attention,
    ),
    CheckBabyBinarySensorDescription(
        key="monitoring_problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda snap, _: bool(snap.problems),
    ),
    CheckBabyBinarySensorDescription(
        key="ai_available",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda snap, _: snap.ai_available,
    ),
    CheckBabyBinarySensorDescription(key="quiet_time", is_on_fn=_quiet_time),
    CheckBabyBinarySensorDescription(
        key="audio_relay",
        device_class=BinarySensorDeviceClass.RUNNING,
        is_on_fn=lambda snap, _: snap.vox_playing,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CheckBabyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the binary sensors of one child."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(CheckBabyBinarySensor(coordinator, description) for description in BINARY_SENSORS)


class CheckBabyBinarySensor(CheckBabyEntity, BinarySensorEntity):
    """A yes/no value read from the monitor snapshot."""

    entity_description: CheckBabyBinarySensorDescription

    def __init__(self, coordinator: CheckBabyCoordinator, description: CheckBabyBinarySensorDescription) -> None:
        """Bind the sensor to its description."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the current value; None shows as unknown."""
        return self.entity_description.is_on_fn(self.snapshot, self.coordinator)
