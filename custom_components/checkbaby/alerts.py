"""Alert lifecycle: raise, notify, repeat, escalate, acknowledge. Pure.

Rules that must hold (tests pin each one):
- A critical alert is never held back by snooze or cooldown.
- Acknowledging stops the notification chain, not the monitoring: the alert
  stays active while its cause lasts and speaks up again if it gets worse.
- Shadow alerts are recorded but never notify and never count towards the level.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .types import ONE_SHOT_KINDS, AlertKind, AlertLevel, Audience, Stage

# Warnings of these kinds also trigger the local channel when nobody reacts.
LOCAL_WARNING_KINDS = frozenset({AlertKind.CRYING, AlertKind.LEFT_BED})


@dataclass(frozen=True)
class AlertTimes:
    """Durations in seconds that drive notification behaviour."""

    critical_repeat_s: float = 30.0
    local_after_s: float = 60.0
    warning_escalate_s: float = 180.0
    cooldown_s: float = 120.0
    one_shot_ttl_s: float = 600.0


@dataclass
class Alert:
    """One active alert."""

    kind: AlertKind
    level: AlertLevel
    detail: dict[str, Any]
    raised_at: float
    level_since: float
    acked: bool = False
    notified: bool = False
    last_push: float = 0.0
    escalated: bool = False
    local_fired: bool = False
    shadow: bool = False
    # Since when a notification has been out without an answer. It survives the
    # alert getting worse: a minute without a reaction is a minute, whatever the level.
    unanswered_since: float | None = None


@dataclass(frozen=True)
class Notification:
    """Something the notifier has to do."""

    kind: AlertKind
    level: AlertLevel
    stage: Stage
    audience: Audience
    detail: dict[str, Any] = field(default_factory=dict[str, Any])


class AlertManager:
    """Holds the active alerts and decides who is told what, and when."""

    def __init__(self, times: AlertTimes | None = None) -> None:
        """Start without alerts."""
        self.times = times or AlertTimes()
        self.active: dict[AlertKind, Alert] = {}
        self.snooze_until = 0.0
        # Babysitter mode: everything goes to everyone.
        self.everyone = False
        # Internet down: the local channel fires at once instead of after a delay.
        self.local_immediately = False
        self._cleared_at: dict[AlertKind, float] = {}
        self._out: list[Notification] = []

    # -- queries ---------------------------------------------------------

    @property
    def level(self) -> AlertLevel:
        """Highest level among the real (non-shadow) alerts."""
        levels = [alert.level for alert in self.active.values() if not alert.shadow]
        return max(levels, default=AlertLevel.NONE)

    @property
    def top(self) -> Alert | None:
        """The most severe real alert; the oldest one wins a tie."""
        real = [alert for alert in self.active.values() if not alert.shadow]
        if not real:
            return None
        return max(real, key=lambda alert: (alert.level, -alert.raised_at))

    def needs_attention(self) -> bool:
        """True while a warning or critical alert is unacknowledged."""
        return any(
            not alert.shadow and not alert.acked and alert.level >= AlertLevel.WARNING
            for alert in self.active.values()
        )

    def local_wanted(self) -> bool:
        """True while an unanswered alert has reached the local alarm channel."""
        return any(alert.local_fired and not alert.acked and not alert.shadow for alert in self.active.values())

    def drain(self) -> list[Notification]:
        """Return and forget the pending notifications."""
        out, self._out = self._out, []
        return out

    # -- changes ---------------------------------------------------------

    def raise_alert(
        self,
        kind: AlertKind,
        level: AlertLevel,
        detail: dict[str, Any],
        now: float,
        *,
        shadow: bool = False,
    ) -> None:
        """Create the alert, or update it; a higher level notifies again."""
        alert = self.active.get(kind)
        if alert is None:
            alert = Alert(kind, level, detail, raised_at=now, level_since=now, shadow=shadow)
            self.active[kind] = alert
            if shadow or level < AlertLevel.WARNING:
                return
            recently_cleared = now - self._cleared_at.get(kind, float("-inf")) < self.times.cooldown_s
            if level is AlertLevel.WARNING and recently_cleared:
                # The same warning flapping back: stay active, but do not push again.
                alert.notified = True
                alert.last_push = now
                return
            self._push(alert, Stage.FIRST, now)
            return

        alert.detail = detail
        if alert.shadow and shadow:
            alert.level = level
            return
        if alert.shadow and not shadow:
            # The alert was only being recorded and is now switched live.
            alert.shadow = False
            alert.level = level
            alert.level_since = now
            alert.acked = False
            if level >= AlertLevel.WARNING:
                self._push(alert, Stage.FIRST, now)
            return
        if shadow:
            # A live alert was switched to record-only: take it off the phones first.
            self.clear(kind, now)
            self.active[kind] = Alert(kind, level, detail, raised_at=now, level_since=now, shadow=True)
            return
        if level > alert.level:
            alert.level = level
            alert.level_since = now
            alert.acked = False
            alert.escalated = False
            # local_fired is kept: a local alarm that is sounding must not pause
            # just because the alert got worse.
            if level >= AlertLevel.WARNING:
                self._push(alert, Stage.UPGRADE, now)
        elif level < alert.level:
            if alert.notified and level < AlertLevel.WARNING <= alert.level:
                # No longer worth a notification: remove the one that is showing.
                alert.notified = False
                self._out.append(Notification(kind, alert.level, Stage.CLEARED, Audience.ALL, alert.detail))
            alert.level = level

    def clear(self, kind: AlertKind, now: float) -> None:
        """The cause is gone."""
        alert = self.active.pop(kind, None)
        if alert is None:
            return
        if alert.notified and not alert.shadow:
            # Only an alert that was on the phones can "flap back": a hint that
            # ends must not swallow the first notification of a real warning.
            self._cleared_at[kind] = now
            self._out.append(Notification(kind, alert.level, Stage.CLEARED, Audience.ALL, alert.detail))

    def acknowledge(self, now: float) -> int:
        """Someone has seen the alerts. Returns how many were acknowledged."""
        count = 0
        for alert in list(self.active.values()):
            if alert.shadow or alert.acked or alert.level < AlertLevel.WARNING:
                continue
            alert.acked = True
            alert.unanswered_since = None
            count += 1
            self._out.append(
                Notification(alert.kind, alert.level, Stage.ACKNOWLEDGED, Audience.ALL, alert.detail)
            )
            if alert.kind in ONE_SHOT_KINDS:
                del self.active[alert.kind]
        return count

    def snooze(self, until: float, now: float) -> None:
        """Hold warnings back until `until`. Critical alerts are not affected."""
        self.snooze_until = until
        for alert in self.active.values():
            if alert.shadow or alert.acked or alert.level is not AlertLevel.WARNING:
                continue
            if alert.notified:
                alert.notified = False
                alert.local_fired = False
                alert.unanswered_since = None
                self._out.append(
                    Notification(alert.kind, alert.level, Stage.ACKNOWLEDGED, Audience.ALL, alert.detail)
                )

    def tick(self, now: float) -> None:
        """Advance repeats, escalation, the local channel and one-shot expiry."""
        for alert in list(self.active.values()):
            if alert.kind in ONE_SHOT_KINDS and now - alert.raised_at >= self.times.one_shot_ttl_s:
                self.clear(alert.kind, now)
                continue
            if alert.shadow or alert.acked or alert.level < AlertLevel.WARNING:
                continue
            if not alert.notified:
                # Held back by snooze; _push decides whether it may go out now.
                self._push(alert, Stage.FIRST, now)
                continue
            age = now - alert.level_since
            if alert.level is AlertLevel.CRITICAL:
                if now - alert.last_push >= self.times.critical_repeat_s:
                    self._push(alert, Stage.REPEAT, now)
            elif not alert.escalated and age >= self.times.warning_escalate_s:
                alert.escalated = True
                self._push(alert, Stage.ESCALATE, now)
            wants_local = alert.level is AlertLevel.CRITICAL or alert.kind in LOCAL_WARNING_KINDS
            waited = now - (alert.unanswered_since if alert.unanswered_since is not None else now)
            local_due = self.local_immediately or waited >= self.times.local_after_s
            if wants_local and local_due and not alert.local_fired:
                alert.local_fired = True
                self._out.append(Notification(alert.kind, alert.level, Stage.LOCAL, Audience.ALL, alert.detail))

    def _push(self, alert: Alert, stage: Stage, now: float) -> None:
        if alert.level < AlertLevel.CRITICAL and now < self.snooze_until:
            alert.notified = False
            return
        to_all = alert.level is AlertLevel.CRITICAL or self.everyone or stage is Stage.ESCALATE
        audience = Audience.ALL if to_all else Audience.ON_DUTY
        alert.notified = True
        alert.last_push = now
        if alert.unanswered_since is None:
            alert.unanswered_since = now
        self._out.append(Notification(alert.kind, alert.level, stage, audience, alert.detail))

    # -- persistence -----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable copy of the active alerts."""
        return {
            "snooze_until": self.snooze_until,
            "active": [
                {
                    "kind": alert.kind.value,
                    "level": int(alert.level),
                    "detail": alert.detail,
                    "raised_at": alert.raised_at,
                    "level_since": alert.level_since,
                    "acked": alert.acked,
                    "notified": alert.notified,
                    "last_push": alert.last_push,
                    "escalated": alert.escalated,
                    "local_fired": alert.local_fired,
                    "shadow": alert.shadow,
                    "unanswered_since": alert.unanswered_since,
                }
                for alert in self.active.values()
            ],
        }

    def restore(self, raw: dict[str, Any] | None) -> None:
        """Take over stored alerts; anything malformed is dropped."""
        if not raw:
            return
        try:
            self.snooze_until = float(raw.get("snooze_until", 0.0))
        except (TypeError, ValueError):
            self.snooze_until = 0.0
        for item in raw.get("active", []):
            try:
                alert = Alert(
                    kind=AlertKind(item["kind"]),
                    level=AlertLevel(int(item["level"])),
                    detail=dict(item.get("detail") or {}),
                    raised_at=float(item["raised_at"]),
                    level_since=float(item["level_since"]),
                    acked=bool(item.get("acked", False)),
                    notified=bool(item.get("notified", False)),
                    last_push=float(item.get("last_push", 0.0)),
                    escalated=bool(item.get("escalated", False)),
                    local_fired=bool(item.get("local_fired", False)),
                    shadow=bool(item.get("shadow", False)),
                    unanswered_since=None if item.get("unanswered_since") is None else float(item["unanswered_since"]),
                )
            except (KeyError, TypeError, ValueError):
                continue
            self.active[alert.kind] = alert
