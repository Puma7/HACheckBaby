"""Deterministic alert rules: which alerts the signals call for right now. Pure.

The result is the full list of rule-based alerts that should be active. The
monitor raises those and clears rule-based alerts that are no longer listed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .alerts import AlertManager
from .climate import climate_level
from .profiles import AgeProfile
from .settings import Settings, left_bed_alert_applies
from .signals import Signals
from .types import AlertKind, AlertLevel, ChildState, VitalFusion

RULE_KINDS = frozenset(
    {
        AlertKind.CRYING,
        AlertKind.NO_BREATHING,
        AlertKind.LEFT_BED,
        AlertKind.PET_IN_BED,
        AlertKind.CLIMATE,
        AlertKind.SMOKE,
        AlertKind.MONITORING_FAILURE,
        AlertKind.INTERNET_DOWN,
    }
)

# A monitoring failure that lasts this long while armed becomes critical.
FAILURE_CRITICAL_S = 300.0
# The room must be outside its range this long before it is mentioned.
CLIMATE_HOLD_S = 600.0


@dataclass(frozen=True)
class Desired:
    """An alert that should be active."""

    kind: AlertKind
    level: AlertLevel
    detail: dict[str, Any] = field(default_factory=dict[str, Any])
    shadow: bool = False


class Durations:
    """Remembers since when named conditions have been true."""

    def __init__(self) -> None:
        """Start with no condition held."""
        self._since: dict[str, float] = {}

    def held(self, key: str, active: bool, now: float) -> float:
        """Return how long the condition has been true without a break."""
        if not active:
            self._since.pop(key, None)
            return 0.0
        return now - self._since.setdefault(key, now)


@dataclass
class RuleContext:
    """Everything the rules look at."""

    signals: Signals
    settings: Settings
    profile: AgeProfile
    state: ChildState
    alerts: AlertManager
    durations: Durations
    problems: list[str]
    left_unattended: bool
    now: float


def no_breathing_movement(ctx: RuleContext) -> list[str] | None:
    """Return the sources that report no sign of life, or None if the rule does not hold.

    Holds only when a usable source that has seen the child breathe or move
    before now sees neither for the configured time. Sources that are not
    usable never count as "no movement".
    """
    signals = ctx.signals
    if signals.presence is False or ctx.state in (ChildState.ATTENDED, ChildState.EMPTY):
        return None
    if signals.motion.active or signals.crying.active or signals.scream.active:
        return None
    quiet = {name: reading.quiet_for(ctx.now) for name, reading in signals.vitals.items()}
    usable = {name: seconds for name, seconds in quiet.items() if seconds is not None}
    if not usable:
        return None
    silent = sorted(name for name, seconds in usable.items() if seconds >= ctx.settings.no_breathing_s)
    if not silent:
        return None
    if ctx.settings.vital_fusion is VitalFusion.ALL and len(silent) < len(usable):
        return None
    return silent


def evaluate(ctx: RuleContext) -> list[Desired]:
    """Return all rule-based alerts that should be active now."""
    signals, settings, now = ctx.signals, ctx.settings, ctx.now
    desired: list[Desired] = []

    # Smoke and CO are passed through no matter what mode the monitor is in.
    if signals.smoke.active:
        desired.append(Desired(AlertKind.SMOKE, AlertLevel.CRITICAL))

    if not settings.armed or settings.privacy:
        ctx.durations.held("failure", False, now)
        ctx.durations.held("climate", False, now)
        return desired

    failure_for = ctx.durations.held("failure", bool(ctx.problems), now)
    if ctx.problems:
        level = AlertLevel.CRITICAL if failure_for >= FAILURE_CRITICAL_S else AlertLevel.WARNING
        desired.append(Desired(AlertKind.MONITORING_FAILURE, level, {"problems": list(ctx.problems)}))

    if signals.internet is False:
        desired.append(Desired(AlertKind.INTERNET_DOWN, AlertLevel.INFO))

    room = climate_level(signals.temperature, settings.temp_min, settings.temp_max)
    climate_for = ctx.durations.held("climate", room is not AlertLevel.NONE, now)
    if room is not AlertLevel.NONE and climate_for >= CLIMATE_HOLD_S:
        desired.append(Desired(AlertKind.CLIMATE, room, {"temperature": signals.temperature}))

    if signals.pet_in_bed.active:
        desired.append(Desired(AlertKind.PET_IN_BED, AlertLevel.WARNING))

    if ctx.state is ChildState.ATTENDED:
        # Someone is with the child; the child-related alerts pause.
        return desired

    crying = ctx.alerts.active.get(AlertKind.CRYING)
    cried_long_enough = (signals.crying.active or signals.scream.active) and signals.distress_for(
        now
    ) >= settings.cry_warning_delay()
    if cried_long_enough or (crying is not None and ctx.state is ChildState.CRYING):
        level = AlertLevel.WARNING
        if crying is not None and (
            crying.level is AlertLevel.CRITICAL
            or (not crying.acked and now - crying.raised_at >= settings.cry_critical_s)
        ):
            level = AlertLevel.CRITICAL
        desired.append(Desired(AlertKind.CRYING, level, {"seconds": round(signals.distress_for(now))}))

    silent = no_breathing_movement(ctx)
    if silent is not None:
        desired.append(
            Desired(
                AlertKind.NO_BREATHING,
                AlertLevel.CRITICAL,
                {"sources": silent},
                shadow=not settings.breathing_alert,
            )
        )

    if ctx.left_unattended and left_bed_alert_applies(ctx.profile):
        desired.append(Desired(AlertKind.LEFT_BED, AlertLevel.WARNING))

    return desired
