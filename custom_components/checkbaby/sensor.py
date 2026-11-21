"""Sensors for CheckBaby."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .ai_schema import POSITION, VERDICT
from .climate import TOG_OPTIONS, tog_recommendation
from .coordinator import CheckBabyCoordinator
from .entity import CheckBabyEntity
from .models import CheckBabyConfigEntry
from .monitor import Snapshot
from .profiles import AgeProfile
from .types import AlertKind, AlertLevel, ChildState

type Value = str | int | float | datetime | None


def _time(epoch: float | None) -> datetime | None:
    return None if epoch is None else dt_util.utc_from_timestamp(epoch)


def _rounded(value: float | None, digits: int = 1) -> float | None:
    return None if value is None else round(value, digits)


@dataclass(frozen=True, kw_only=True)
class CheckBabySensorDescription(SensorEntityDescription):
    """A sensor and how its value is read."""

    value_fn: Callable[[Snapshot, CheckBabyCoordinator], Value]
    attributes_fn: Callable[[Snapshot, CheckBabyCoordinator], dict[str, Any]] | None = None


def _assessment_attributes(snapshot: Snapshot, coordinator: CheckBabyCoordinator) -> dict[str, Any]:
    assessment = snapshot.assessment
    if assessment is None:
        return {}
    return {
        "reason": assessment.reason,
        "position": assessment.position,
        "airway_risk": assessment.airway_risk,
        "face_visible": assessment.face_visible,
        "hazards": list(assessment.hazards),
        "confidence": assessment.confidence,
        "assessed_at": _time(assessment.at),
    }


SENSORS: tuple[CheckBabySensorDescription, ...] = (
    CheckBabySensorDescription(
        key="state",
        device_class=SensorDeviceClass.ENUM,
        options=[state.value for state in ChildState],
        value_fn=lambda snap, _: snap.state.value,
        attributes_fn=lambda snap, _: {"since": _time(snap.state_since)},
    ),
    CheckBabySensorDescription(
        key="alert_level",
        device_class=SensorDeviceClass.ENUM,
        options=[level.name.lower() for level in AlertLevel],
        value_fn=lambda snap, _: snap.level.name.lower(),
        attributes_fn=lambda snap, _: {"alerts": list(snap.alerts)},
    ),
    CheckBabySensorDescription(
        key="alert_reason",
        device_class=SensorDeviceClass.ENUM,
        options=["none", *(kind.value for kind in AlertKind)],
        value_fn=lambda snap, _: snap.alert_kind.value if snap.alert_kind else "none",
        attributes_fn=lambda snap, _: dict(snap.alert_detail),
    ),
    CheckBabySensorDescription(
        key="noise_level",
        native_unit_of_measurement="dBFS",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda snap, _: _rounded(snap.level_db),
    ),
    CheckBabySensorDescription(
        key="noise_floor",
        native_unit_of_measurement="dBFS",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda snap, _: _rounded(snap.baseline_db),
    ),
    CheckBabySensorDescription(
        key="last_motion",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda snap, _: _time(snap.last_motion),
    ),
    CheckBabySensorDescription(
        key="asleep_since",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda snap, _: _time(snap.asleep_since),
    ),
    CheckBabySensorDescription(
        key="last_sleep_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        suggested_display_precision=0,
        value_fn=lambda snap, _: None if snap.last_sleep_s is None else round(snap.last_sleep_s / 60),
    ),
    CheckBabySensorDescription(
        key="sleep_today",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=1,
        value_fn=lambda snap, _: round(snap.slept_today_s / 3600, 2),
    ),
    CheckBabySensorDescription(
        key="crying_today",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        suggested_display_precision=0,
        value_fn=lambda snap, _: round(snap.cried_today_s / 60),
    ),
    CheckBabySensorDescription(
        key="wakeups_tonight",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda snap, _: snap.wakeups_tonight,
    ),
    CheckBabySensorDescription(
        key="breathing_rate",
        native_unit_of_measurement="/min",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda snap, _: _rounded(snap.breathing_rate),
    ),
    CheckBabySensorDescription(
        key="heart_rate",
        native_unit_of_measurement="bpm",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda _, coordinator: _rounded(coordinator.heart_rate),
    ),
    CheckBabySensorDescription(
        key="sleeping_bag",
        device_class=SensorDeviceClass.ENUM,
        options=list(TOG_OPTIONS),
        value_fn=lambda snap, _: tog_recommendation(snap.temperature),
    ),
    CheckBabySensorDescription(
        key="ai_assessment",
        device_class=SensorDeviceClass.ENUM,
        options=list(VERDICT),
        value_fn=lambda snap, _: snap.assessment.verdict if snap.assessment else None,
        attributes_fn=_assessment_attributes,
    ),
    CheckBabySensorDescription(
        key="position",
        device_class=SensorDeviceClass.ENUM,
        options=list(POSITION),
        value_fn=lambda snap, _: snap.assessment.position if snap.assessment else None,
    ),
    CheckBabySensorDescription(
        key="monitoring_problems",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda snap, _: len(snap.problems),
        attributes_fn=lambda snap, _: {"problems": list(snap.problems)},
    ),
    CheckBabySensorDescription(
        key="ai_calls_last_hour",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda _, coordinator: coordinator.budget.used(dt_util.utcnow().timestamp()),
    ),
    CheckBabySensorDescription(
        key="age_profile",
        device_class=SensorDeviceClass.ENUM,
        options=[profile.value for profile in AgeProfile],
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda _, coordinator: coordinator.profile.value,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CheckBabyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the sensors of one child."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(CheckBabySensor(coordinator, description) for description in SENSORS)


class CheckBabySensor(CheckBabyEntity, SensorEntity):
    """A value read from the monitor snapshot."""

    entity_description: CheckBabySensorDescription

    def __init__(self, coordinator: CheckBabyCoordinator, description: CheckBabySensorDescription) -> None:
        """Bind the sensor to its description."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Value:
        """Return the current value."""
        return self.entity_description.value_fn(self.snapshot, self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the extra attributes, if the sensor has any."""
        attributes_fn = self.entity_description.attributes_fn
        return attributes_fn(self.snapshot, self.coordinator) if attributes_fn else None
