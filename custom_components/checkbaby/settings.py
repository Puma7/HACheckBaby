"""User-adjustable settings of one child. Pure, no Home Assistant imports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any

from .profiles import AgeProfile
from .types import ON_DUTY_ALL, Mode, Sensitivity, VitalFusion

SENSITIVITY_FACTOR = {Sensitivity.LOW: 2.0, Sensitivity.MEDIUM: 1.0, Sensitivity.HIGH: 0.5}


@dataclass
class Settings:
    """Everything the entities can change. Persisted across restarts."""

    armed: bool = False
    mode: Mode = Mode.NIGHT
    privacy: bool = False
    # On by default: the assessment only runs once AI tasks and consent are set
    # in the options, so this switch is a pause button, not a second place to enable it.
    ai_enabled: bool = True
    breathing_alert: bool = False
    vox_enabled: bool = False
    on_duty: str = ON_DUTY_ALL
    sensitivity: Sensitivity = Sensitivity.MEDIUM
    vital_fusion: VitalFusion = VitalFusion.ALL
    active_place: str | None = None
    cry_warning_s: float = 15.0
    cry_critical_s: float = 180.0
    noise_margin_db: float = 15.0
    no_breathing_s: float = 20.0
    ai_interval_min: float = 10.0
    temp_min: float = 16.0
    temp_max: float = 22.0
    snooze_until: float = 0.0

    def cry_warning_delay(self) -> float:
        """Seconds of crying before a warning, scaled by sensitivity and mode."""
        delay = self.cry_warning_s * SENSITIVITY_FACTOR[self.sensitivity]
        if self.mode is Mode.BABYSITTER:
            delay *= 0.5
        return delay

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable copy."""
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> Settings:
        """Build settings from stored data; unknown or invalid values fall back to defaults."""
        result = cls()
        if not raw:
            return result
        for item in fields(cls):
            if item.name not in raw:
                continue
            default = getattr(result, item.name)
            value = raw[item.name]
            try:
                if isinstance(default, bool):
                    coerced: Any = bool(value)
                elif isinstance(default, (Mode, Sensitivity, VitalFusion)):
                    coerced = type(default)(value)
                elif isinstance(default, float):
                    coerced = float(value)
                elif item.name == "active_place":
                    coerced = None if value is None else str(value)
                else:
                    coerced = str(value)
            except (TypeError, ValueError):
                continue
            setattr(result, item.name, coerced)
        return result


def prone_alert_applies(profile: AgeProfile) -> bool:
    """Prone position is flagged in the first year only."""
    return profile in (AgeProfile.NEWBORN, AgeProfile.INFANT)


def prone_can_be_critical(profile: AgeProfile) -> bool:
    """Only for newborns: older infants may roll over on their own."""
    return profile is AgeProfile.NEWBORN


def left_bed_alert_applies(profile: AgeProfile) -> bool:
    """A child leaving the bed on its own is a toddler topic."""
    return profile is AgeProfile.TODDLER
