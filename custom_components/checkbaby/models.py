"""Runtime data of a CheckBaby config entry."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from homeassistant.config_entries import ConfigEntry


@dataclass(frozen=True, slots=True)
class CheckBabyData:
    """What one config entry (one child) holds at runtime."""

    child_name: str
    birth_date: date


type CheckBabyConfigEntry = ConfigEntry[CheckBabyData]
