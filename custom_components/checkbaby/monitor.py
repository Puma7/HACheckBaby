"""The monitor core: signals in, child state and notifications out. Pure.

No Home Assistant imports and no clock of its own: every method takes `now`
(epoch seconds), so whole nights can be replayed in tests.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
from typing import Any

from .ai_policy import MIN_CONFIDENCE, evaluate_assessment, needs_recheck
from .ai_schema import Assessment
from .alerts import AlertManager, AlertTimes, Notification
from .profiles import AgeProfile
from .rules import RULE_KINDS, Durations, RuleContext, evaluate
from .settings import Settings
from .signals import Signals
from .sleep_log import SleepLog
from .state_machine import DEFAULT_TIMES, StateTimes, next_state
from .types import AI_KINDS, AlertKind, AlertLevel, ChildState
from .vox import VoxAction, VoxController
from .watchdog import Watchdog

# A warning from the AI is looked at again this soon, with a fresh image.
RECHECK_AFTER_S = 15.0
MAX_EVENTS = 300
MICROPHONE = "microphone"
# Watchdog names of the sources behind the breathing-movement hint.
VITAL_SOURCES = frozenset({"engine", "vital_sensor"})


@dataclass(frozen=True)
class Snapshot:
    """What the entities show."""

    state: ChildState
    state_since: float
    level: AlertLevel
    alert_kind: AlertKind | None
    alert_detail: dict[str, Any]
    needs_attention: bool
    alerts: tuple[dict[str, Any], ...]
    problems: tuple[str, ...]
    crying: bool
    motion: bool
    in_bed: bool | None
    attended: bool
    breathing: bool | None
    breathing_rate: float | None
    level_db: float | None
    baseline_db: float | None
    temperature: float | None
    humidity: float | None
    last_motion: float | None
    asleep_since: float | None
    last_sleep_s: float | None
    slept_today_s: float
    cried_today_s: float
    wakeups_tonight: int
    vox_playing: bool
    assessment: Assessment | None
    ai_available: bool | None


class Monitor:
    """Everything about one child that does not need Home Assistant."""

    def __init__(
        self,
        settings: Settings,
        now: float,
        *,
        state_times: StateTimes = DEFAULT_TIMES,
        alert_times: AlertTimes | None = None,
    ) -> None:
        """Start with nothing known."""
        self.settings = settings
        self.signals = Signals()
        self.watchdog = Watchdog(now)
        self.alerts = AlertManager(alert_times)
        self.sleep_log = SleepLog()
        self.vox = VoxController()
        self.durations = Durations()
        self.state = ChildState.UNKNOWN
        self.state_since = now
        self.problems: list[str] = []
        self.assessment: Assessment | None = None
        self.ai_available: bool | None = None
        self.left_unattended = False
        self.last_motion: float | None = None
        self.events: deque[dict[str, Any]] = deque(maxlen=MAX_EVENTS)
        self._state_times = state_times
        self._ai_request: str | None = None
        self._last_ai = now
        self._recheck_at: float | None = None
        self._vox_action: VoxAction | None = None

    # -- inputs ------------------------------------------------------------

    def set_presence(self, in_bed: bool | None, now: float) -> None:
        """The presence sensor reported whether the child is in bed."""
        if self.signals.presence is True and in_bed is False and not self.signals.caregiver_present(now):
            self.left_unattended = True
        if in_bed is not False:
            self.left_unattended = False
        self.signals.presence = in_bed

    def set_motion(self, active: bool, now: float) -> None:
        """The camera reported movement."""
        if active or self.signals.motion.active:
            # Also when it ends: that is the latest moment something moved.
            self.signals.last_gross = now
        self.signals.motion.set(active, now)
        if active:
            self.last_motion = now

    def change_place(self, now: float) -> None:
        """A different sleep place is active: forget what the old one reported."""
        self.signals = Signals()
        self.durations = Durations()
        self.left_unattended = False
        self.assessment = None
        self.watchdog.restart_grace(now)
        self._log("place_changed", now, place=self.settings.active_place)

    # -- the clock ---------------------------------------------------------

    def tick(self, now: float, profile: AgeProfile) -> None:
        """Re-evaluate state, rules and notification timing."""
        settings = self.settings
        active = settings.armed and not settings.privacy
        self.alerts.everyone = settings.mode.value == "babysitter"
        self.alerts.local_immediately = self.signals.internet is False
        self.alerts.snooze_until = settings.snooze_until

        problems = self.watchdog.problems(now)
        if self.signals.microphone_flat(now):
            problems.append(MICROPHONE)
        if problems != self.problems:
            self._log("problems", now, problems=list(problems))
        self.problems = problems

        # The state must not lag behind the warning: with a short warning delay
        # the phone would say "crying" while the state still says "asleep".
        confirm = min(self._state_times.cry_confirm_s, settings.cry_warning_delay())
        new_state = next_state(
            self.state,
            self.state_since,
            self.signals,
            usable=self.watchdog.usable(now) and not settings.privacy,
            now=now,
            times=replace(self._state_times, cry_confirm_s=confirm),
        )
        if new_state is not self.state:
            self._enter(new_state, now)
        if self.state is ChildState.ATTENDED:
            self.left_unattended = False
            # The child may be lifted out; breathing has to be seen again afterwards.
            self.signals.forget_breathing()

        desired = evaluate(
            RuleContext(
                signals=self.signals,
                settings=settings,
                profile=profile,
                state=self.state,
                alerts=self.alerts,
                durations=self.durations,
                problems=self.problems,
                minor_problems=self._minor_problems(),
                left_unattended=self.left_unattended,
                now=now,
            )
        )
        wanted = {item.kind for item in desired}
        for item in desired:
            is_new = item.kind not in self.alerts.active
            self.alerts.raise_alert(item.kind, item.level, item.detail, now, shadow=item.shadow)
            if is_new:
                self._log("alert", now, kind=item.kind.value, level=int(item.level), shadow=item.shadow, detail=item.detail)
                if item.kind is AlertKind.NO_BREATHING:
                    self._ai_request = "no_breathing"
        for kind in RULE_KINDS - wanted:
            if kind in self.alerts.active:
                self.alerts.clear(kind, now)
                self._log("alert_cleared", now, kind=kind.value)
        if not active or self.state is ChildState.ATTENDED:
            # The AI alerts pause with the child-related rules.
            for kind in AI_KINDS:
                self.alerts.clear(kind, now)
            self._recheck_at = None

        self.alerts.tick(now)

        signals = self.signals
        noise_for = max(signals.loud.active_for(now), signals.crying.active_for(now))
        quiet_for = min(signals.loud.inactive_for(now), signals.crying.inactive_for(now))
        action = self.vox.update(enabled=active and settings.vox_enabled, noise_for=noise_for, quiet_for=quiet_for)
        if action is not None:
            self._vox_action = action

        if active and settings.ai_enabled and self.state is not ChildState.ATTENDED:
            if self._recheck_at is not None and now >= self._recheck_at:
                self._recheck_at = None
                self._ai_request = "recheck"
            elif self._ai_request is None and now - self._last_ai >= settings.ai_interval_min * 60.0:
                self._ai_request = "routine"
        else:
            self._ai_request = None

    def _minor_problems(self) -> frozenset[str]:
        """Problems that are shown but do not notify.

        A lost vital source counts fully once the breathing-movement alert is
        switched on: then an alert depends on it.
        """
        minor = {name for name in self.problems if self.watchdog.minor(name)}
        if self.settings.breathing_alert:
            minor -= VITAL_SOURCES
        return frozenset(minor)

    def serious_problems(self) -> list[str]:
        """Problems that mean the monitor cannot be relied on right now."""
        minor = self._minor_problems()
        return [name for name in self.problems if name not in minor]

    def _enter(self, new_state: ChildState, now: float) -> None:
        previous = self.state
        self.sleep_log.on_state(
            previous, new_state, now, mode=self.settings.mode.value, place=self.settings.active_place
        )
        self.state = new_state
        self.state_since = now
        self._log("state", now, previous=previous.value, state=new_state.value)
        if new_state in (ChildState.CRYING, ChildState.AWAKE):
            self._ai_request = "state_change"

    # -- AI ----------------------------------------------------------------

    def take_ai_request(self, now: float) -> str | None:
        """Return why an assessment is due, once, or None."""
        reason, self._ai_request = self._ai_request, None
        if reason is not None:
            self._last_ai = now
        return reason

    def apply_assessment(self, assessment: Assessment, now: float, profile: AgeProfile, reason: str) -> None:
        """Take in a validated AI answer. It can only touch the AI alert kinds."""
        previous = self.assessment
        self.assessment = assessment
        self.ai_available = True
        self._log(
            "assessment",
            now,
            reason=reason,
            verdict=assessment.verdict,
            position=assessment.position,
            airway_risk=assessment.airway_risk,
            confidence=assessment.confidence,
        )
        active = self.settings.armed and not self.settings.privacy
        if not active or self.state is ChildState.ATTENDED:
            return
        desired = evaluate_assessment(assessment, previous, profile)
        wanted = {item.kind for item in desired}
        unsure = assessment.confidence < MIN_CONFIDENCE
        for item in desired:
            existing = self.alerts.active.get(item.kind)
            if existing is not None and unsure and item.level < existing.level >= AlertLevel.WARNING:
                # An unsure look does not lower a warning either.
                continue
            self.alerts.raise_alert(item.kind, item.level, item.detail, now)
            if existing is None:
                self._log("alert", now, kind=item.kind.value, level=int(item.level), source="ai")
        for kind in AI_KINDS - wanted:
            existing = self.alerts.active.get(kind)
            if existing is None:
                continue
            # An unsure look is not enough to take back a warning.
            if existing.level >= AlertLevel.WARNING and unsure:
                continue
            self.alerts.clear(kind, now)
            self._log("alert_cleared", now, kind=kind.value)
        # One confirming look, never a loop of rechecks.
        if reason != "recheck" and needs_recheck(desired):
            self._recheck_at = now + RECHECK_AFTER_S

    def ai_failed(self, now: float, error: str) -> None:
        """The AI did not answer usefully. Deterministic alerts are unaffected."""
        if self.ai_available is not False:
            self._log("ai_failed", now, error=error)
        self.ai_available = False

    # -- user actions ------------------------------------------------------

    def acknowledge(self, now: float) -> int:
        """Someone has seen the alerts."""
        count = self.alerts.acknowledge(now)
        self._log("acknowledged", now, count=count)
        return count

    def snooze(self, seconds: float, now: float) -> None:
        """Hold warnings back for a while; critical alerts still come through."""
        self.settings.snooze_until = now + seconds
        self.alerts.snooze(self.settings.snooze_until, now)
        self._log("snoozed", now, seconds=seconds)

    def test_alert(self, now: float, level: AlertLevel = AlertLevel.CRITICAL) -> None:
        """Raise a test alert that runs the full notification chain."""
        self.alerts.clear(AlertKind.TEST, now)
        self.alerts.raise_alert(AlertKind.TEST, level, {}, now)
        self._log("test_alert", now, level=int(level))

    def report_interruption(self, seconds: float, now: float) -> None:
        """Monitoring was down while armed, e.g. during a restart."""
        self.alerts.raise_alert(AlertKind.INTERRUPTION, AlertLevel.WARNING, {"seconds": round(seconds)}, now)
        self._log("interruption", now, seconds=round(seconds))

    def force_state(self, state: ChildState, now: float) -> None:
        """Manually mark the child as asleep or awake."""
        if state is not self.state:
            self._enter(state, now)

    # -- outputs -----------------------------------------------------------

    def drain_notifications(self) -> list[Notification]:
        """Return and forget the pending notifications."""
        return self.alerts.drain()

    def take_vox_action(self) -> VoxAction | None:
        """Return and forget the pending audio relay action."""
        action, self._vox_action = self._vox_action, None
        return action

    def _log(self, event: str, now: float, /, **detail: Any) -> None:
        self.events.append({"at": now, "type": event, **detail})

    def _breathing(self, now: float) -> tuple[bool | None, float | None]:
        usable = [reading for reading in self.signals.vitals.values() if reading.usable(now)]
        if not usable:
            return None, None
        rate = next((reading.rate for reading in usable if reading.rate is not None), None)
        return any(reading.breathing for reading in usable), rate

    def snapshot(self, now: float, day_start: float, night_start: float) -> Snapshot:
        """Return the values the entities show."""
        top = self.alerts.top
        breathing, rate = self._breathing(now)
        signals = self.signals
        return Snapshot(
            state=self.state,
            state_since=self.state_since,
            level=self.alerts.level,
            alert_kind=top.kind if top else None,
            alert_detail=dict(top.detail) if top else {},
            needs_attention=self.alerts.needs_attention(),
            alerts=tuple(
                {
                    "kind": alert.kind.value,
                    "level": alert.level.name.lower(),
                    "acknowledged": alert.acked,
                    "shadow": alert.shadow,
                    "since": alert.raised_at,
                }
                for alert in self.alerts.active.values()
            ),
            problems=tuple(self.problems),
            crying=signals.crying.active or signals.scream.active,
            motion=signals.motion.active,
            in_bed=signals.presence,
            attended=self.state is ChildState.ATTENDED,
            breathing=breathing,
            breathing_rate=rate,
            level_db=signals.level_db,
            baseline_db=signals.baseline_db,
            temperature=signals.temperature,
            humidity=signals.humidity,
            last_motion=self.last_motion,
            asleep_since=self.sleep_log.asleep_since(),
            last_sleep_s=self.sleep_log.last_session_seconds(),
            slept_today_s=self.sleep_log.slept_between(day_start, now),
            cried_today_s=self.sleep_log.cried_between(day_start, now),
            wakeups_tonight=self.sleep_log.wakeups_between(night_start, now),
            vox_playing=self.vox.playing,
            assessment=self.assessment,
            ai_available=self.ai_available,
        )

    # -- persistence -------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Return what must survive a restart."""
        return {
            "settings": self.settings.to_dict(),
            "alerts": self.alerts.to_dict(),
            "sleep_log": self.sleep_log.to_dict(),
            "baseline_db": self.signals.baseline_db,
        }

    def restore(self, raw: dict[str, Any] | None) -> None:
        """Take over stored alerts, sleep log and noise floor."""
        if not raw:
            return
        self.alerts.restore(raw.get("alerts"))
        self.sleep_log.restore(raw.get("sleep_log"))
        baseline = raw.get("baseline_db")
        if isinstance(baseline, (int, float)):
            self.signals.baseline_db = float(baseline)
