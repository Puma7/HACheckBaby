"""Runtime data of a CheckBaby config entry."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry

from .const import (
    CONF_AUDIO_URL,
    CONF_BED_ZONE,
    CONF_BREATH_RATE_ENTITY,
    CONF_CAMERA_ENTITY,
    CONF_CRY_ENTITY,
    CONF_DOOR_ENTITY,
    CONF_ENGINE_ID,
    CONF_FRIGATE_CAMERA,
    CONF_HEART_RATE_ENTITY,
    CONF_HUMIDITY_ENTITY,
    CONF_LEVEL_ENTITY,
    CONF_MOTION_ENTITY,
    CONF_PERSON_IS_CAREGIVER,
    CONF_PRESENCE_ENTITY,
    CONF_TEMPERATURE_ENTITY,
)

if TYPE_CHECKING:
    from .coordinator import CheckBabyCoordinator


def _text(data: Mapping[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


@dataclass(frozen=True, slots=True)
class SleepPlace:
    """One place where the child sleeps, with its camera and sensors."""

    place_id: str
    name: str
    frigate_camera: str | None = None
    camera_entity: str | None = None
    bed_zone: str | None = None
    person_is_caregiver: bool = False
    presence_entity: str | None = None
    door_entity: str | None = None
    temperature_entity: str | None = None
    humidity_entity: str | None = None
    breath_rate_entity: str | None = None
    heart_rate_entity: str | None = None
    engine_id: str | None = None
    audio_url: str | None = None
    cry_entity: str | None = None
    motion_entity: str | None = None
    level_entity: str | None = None

    @classmethod
    def from_data(cls, place_id: str, name: str, data: Mapping[str, Any]) -> SleepPlace:
        """Build a sleep place from sub-entry data."""
        return cls(
            place_id=place_id,
            name=name,
            frigate_camera=_text(data, CONF_FRIGATE_CAMERA),
            camera_entity=_text(data, CONF_CAMERA_ENTITY),
            bed_zone=_text(data, CONF_BED_ZONE),
            person_is_caregiver=bool(data.get(CONF_PERSON_IS_CAREGIVER, False)),
            presence_entity=_text(data, CONF_PRESENCE_ENTITY),
            door_entity=_text(data, CONF_DOOR_ENTITY),
            temperature_entity=_text(data, CONF_TEMPERATURE_ENTITY),
            humidity_entity=_text(data, CONF_HUMIDITY_ENTITY),
            breath_rate_entity=_text(data, CONF_BREATH_RATE_ENTITY),
            heart_rate_entity=_text(data, CONF_HEART_RATE_ENTITY),
            engine_id=_text(data, CONF_ENGINE_ID),
            audio_url=_text(data, CONF_AUDIO_URL),
            cry_entity=_text(data, CONF_CRY_ENTITY),
            motion_entity=_text(data, CONF_MOTION_ENTITY),
            level_entity=_text(data, CONF_LEVEL_ENTITY),
        )


@dataclass(slots=True)
class CheckBabyData:
    """What one config entry (one child) holds at runtime."""

    child_name: str
    birth_date: date
    coordinator: CheckBabyCoordinator


type CheckBabyConfigEntry = ConfigEntry[CheckBabyData]
