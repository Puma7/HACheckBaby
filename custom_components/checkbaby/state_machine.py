"""Child state from signals. Pure, no Home Assistant imports.

Transitions depend on how long something has lasted, never on a single event.
"""

from __future__ import annotations

from dataclasses import dataclass

from .signals import Signals
from .types import ChildState


@dataclass(frozen=True)
class StateTimes:
    """Durations in seconds that drive the transitions."""

    cry_confirm_s: float = 8.0
    scream_confirm_s: float = 3.0
    crying_calm_s: float = 60.0
    restless_after_s: float = 20.0
    awake_after_s: float = 180.0
    restless_calm_s: float = 120.0
    awake_calm_s: float = 300.0


DEFAULT_TIMES = StateTimes()


def next_state(
    previous: ChildState,
    state_since: float,
    signals: Signals,
    *,
    usable: bool,
    now: float,
    times: StateTimes = DEFAULT_TIMES,
) -> ChildState:
    """Return the state that follows from the signals.

    `usable` is False when the core sources are down: then nothing is known,
    and the state must say so instead of defaulting to something harmless.
    """
    if not usable:
        return ChildState.UNKNOWN
    if signals.caregiver_present(now):
        return ChildState.ATTENDED
    if signals.presence is False:
        return ChildState.EMPTY

    if signals.distress(times.cry_confirm_s, times.scream_confirm_s, now):
        return ChildState.CRYING
    if previous is ChildState.CRYING:
        # Crying only ends after a stretch of quiet; the child is awake then.
        if signals.distress_quiet_for(now) < times.crying_calm_s:
            return ChildState.CRYING
        return ChildState.AWAKE

    # Calm only counts from the moment the current state began.
    calm = min(signals.calm_for(now), now - state_since)
    if previous is ChildState.AWAKE:
        return ChildState.ASLEEP if calm >= times.awake_calm_s else ChildState.AWAKE
    if previous in (ChildState.ATTENDED, ChildState.EMPTY, ChildState.UNKNOWN):
        # Just put down or just visible again: assume awake until it stays calm.
        if previous is ChildState.UNKNOWN and not signals.activity():
            return ChildState.ASLEEP
        return ChildState.AWAKE
    if previous is ChildState.RESTLESS:
        if signals.activity() and now - state_since >= times.awake_after_s:
            return ChildState.AWAKE
        return ChildState.ASLEEP if calm >= times.restless_calm_s else ChildState.RESTLESS

    # previous is ASLEEP
    if signals.activity_for(now) >= times.restless_after_s:
        return ChildState.RESTLESS
    return ChildState.ASLEEP
