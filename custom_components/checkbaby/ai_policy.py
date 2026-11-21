"""What an AI assessment may do. Pure, no Home Assistant imports.

Guard rails:
- The AI only ever produces alerts of its own kinds (see AI_KINDS). It has no
  way to clear or lower an alert that came from a deterministic rule.
- On its own it reaches "warning". "Critical" needs a defined danger that a
  second assessment of a fresh image confirms.
"""

from __future__ import annotations

from collections import deque

from .ai_schema import Assessment
from .profiles import AgeProfile
from .rules import Desired
from .settings import prone_alert_applies, prone_can_be_critical
from .types import AlertKind, AlertLevel

# A previous assessment confirms the current one only if it is this recent.
CONFIRM_WINDOW_S = 180.0
# Below this confidence the assessment raises nothing above a hint.
MIN_CONFIDENCE = 0.5


def _airway(assessment: Assessment) -> bool:
    return assessment.presence == "in_bed" and assessment.airway_risk == "likely"


def _prone(assessment: Assessment) -> bool:
    return assessment.presence == "in_bed" and assessment.position == "prone"


def evaluate_assessment(
    current: Assessment, previous: Assessment | None, profile: AgeProfile
) -> list[Desired]:
    """Return the AI alerts that should be active after this assessment."""
    confirming = previous if previous and current.at - previous.at <= CONFIRM_WINDOW_S else None
    confident = current.confidence >= MIN_CONFIDENCE
    desired: list[Desired] = []
    detail = {"reason": current.reason, "confidence": current.confidence}

    if _airway(current) and confident:
        confirmed = confirming is not None and _airway(confirming)
        level = AlertLevel.CRITICAL if confirmed else AlertLevel.WARNING
        desired.append(Desired(AlertKind.AIRWAY_RISK, level, detail))
    elif current.presence == "in_bed" and current.airway_risk != "none":
        desired.append(Desired(AlertKind.AIRWAY_RISK, AlertLevel.INFO, detail))

    if _prone(current) and prone_alert_applies(profile):
        level = AlertLevel.WARNING if confident else AlertLevel.INFO
        if confident and prone_can_be_critical(profile) and confirming is not None and _prone(confirming):
            level = AlertLevel.CRITICAL
        desired.append(Desired(AlertKind.PRONE_POSITION, level, detail))

    if current.hazards:
        desired.append(Desired(AlertKind.HAZARD, AlertLevel.INFO, {**detail, "hazards": list(current.hazards)}))

    if not current.view_ok:
        confirmed = confirming is not None and not confirming.view_ok
        level = AlertLevel.WARNING if confirmed else AlertLevel.INFO
        desired.append(Desired(AlertKind.CAMERA_VIEW, level, detail))

    return desired


def needs_recheck(desired: list[Desired]) -> bool:
    """True when a warning waits for its confirming second look."""
    return any(
        item.level is AlertLevel.WARNING
        and item.kind in (AlertKind.AIRWAY_RISK, AlertKind.PRONE_POSITION)
        or item.kind is AlertKind.CAMERA_VIEW
        and item.level is AlertLevel.INFO
        for item in desired
    )


class Budget:
    """Caps the number of AI calls per hour."""

    def __init__(self, per_hour: int = 30) -> None:
        """Allow up to `per_hour` calls in any sliding hour."""
        self.per_hour = per_hour
        self._calls: deque[float] = deque()

    def _trim(self, now: float) -> None:
        while self._calls and now - self._calls[0] >= 3600.0:
            self._calls.popleft()

    def allow(self, now: float) -> bool:
        """True if another call fits into the budget."""
        self._trim(now)
        return len(self._calls) < self.per_hour

    def record(self, now: float) -> None:
        """Count a call."""
        self._calls.append(now)

    def used(self, now: float) -> int:
        """Calls in the last hour."""
        self._trim(now)
        return len(self._calls)
