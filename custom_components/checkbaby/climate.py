"""Room climate rules. Pure, no Home Assistant imports."""

from __future__ import annotations

from .types import AlertLevel

# Outside the range by more than this many degrees is a warning, not a hint.
WARNING_MARGIN_C = 3.0

# Sleeping bag thickness by room temperature: upper bound in degrees Celsius
# and the usual manufacturer guidance. A guideline, not a rule.
_TOG_STEPS: tuple[tuple[float, str], ...] = (
    (16.0, "tog_3_5"),
    (18.0, "tog_2_5_plus_layer"),
    (21.0, "tog_2_5"),
    (24.0, "tog_1_0"),
    (27.0, "tog_0_5"),
)
TOG_OPTIONS: tuple[str, ...] = (*(step[1] for step in _TOG_STEPS), "tog_0_2")


def tog_recommendation(temperature: float | None) -> str | None:
    """Return the sleeping bag suggestion for a room temperature."""
    if temperature is None:
        return None
    for upper, label in _TOG_STEPS:
        if temperature < upper:
            return label
    return "tog_0_2"


def climate_level(temperature: float | None, temp_min: float, temp_max: float) -> AlertLevel:
    """How far the room is outside the configured range."""
    if temperature is None or temp_min <= temperature <= temp_max:
        return AlertLevel.NONE
    distance = temp_min - temperature if temperature < temp_min else temperature - temp_max
    return AlertLevel.WARNING if distance > WARNING_MARGIN_C else AlertLevel.INFO
