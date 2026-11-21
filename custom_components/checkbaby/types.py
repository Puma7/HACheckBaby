"""Shared enums and value types. Pure, no Home Assistant imports."""

from __future__ import annotations

from enum import IntEnum, StrEnum


class ChildState(StrEnum):
    """What the child is doing, as far as the signals tell."""

    EMPTY = "empty"
    ASLEEP = "asleep"
    RESTLESS = "restless"
    AWAKE = "awake"
    CRYING = "crying"
    ATTENDED = "attended"
    UNKNOWN = "unknown"


class AlertLevel(IntEnum):
    """Alert severity. Higher wins."""

    NONE = 0
    INFO = 1
    WARNING = 2
    CRITICAL = 3


class AlertKind(StrEnum):
    """Why an alert exists."""

    CRYING = "crying"
    NO_BREATHING = "no_breathing"
    AIRWAY_RISK = "airway_risk"
    PRONE_POSITION = "prone_position"
    HAZARD = "hazard"
    CAMERA_VIEW = "camera_view"
    LEFT_BED = "left_bed"
    PET_IN_BED = "pet_in_bed"
    CLIMATE = "climate"
    SMOKE = "smoke"
    MONITORING_FAILURE = "monitoring_failure"
    INTERNET_DOWN = "internet_down"
    INTERRUPTION = "interruption"
    TEST = "test"


# Alerts that come from the AI assessment. Everything else is deterministic.
AI_KINDS = frozenset(
    {AlertKind.AIRWAY_RISK, AlertKind.PRONE_POSITION, AlertKind.HAZARD, AlertKind.CAMERA_VIEW}
)
# One-shot alerts that no rule keeps alive; they end on acknowledgement or timeout.
ONE_SHOT_KINDS = frozenset({AlertKind.INTERRUPTION, AlertKind.TEST})


class Mode(StrEnum):
    """How the monitor is being used right now."""

    NIGHT = "night"
    NAP = "nap"
    BABYSITTER = "babysitter"


class Sensitivity(StrEnum):
    """Scales how long crying must last before it warns."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class VitalFusion(StrEnum):
    """How several vital sources combine into one no-breathing-movement decision."""

    ANY = "any"
    ALL = "all"


class Audience(StrEnum):
    """Who a notification goes to."""

    ON_DUTY = "on_duty"
    ALL = "all"


class Stage(StrEnum):
    """Why a notification is sent."""

    FIRST = "first"
    UPGRADE = "upgrade"
    REPEAT = "repeat"
    ESCALATE = "escalate"
    LOCAL = "local"
    CLEARED = "cleared"
    ACKNOWLEDGED = "acknowledged"


ON_DUTY_ALL = "all"
