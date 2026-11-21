"""Sleep sessions, wake-ups and crying time. Pure, no Home Assistant imports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .types import ChildState

# A new sleep that starts this soon after the last one continues that session.
MERGE_GAP_S = 20 * 60.0
MAX_SESSIONS = 500
MAX_INTERVALS = 2000

_SLEEPING = (ChildState.ASLEEP, ChildState.RESTLESS)
_ENDS_SLEEP = (ChildState.AWAKE, ChildState.CRYING, ChildState.EMPTY, ChildState.ATTENDED)


@dataclass
class SleepSession:
    """One stretch of sleep; `end` is None while it lasts."""

    start: float
    end: float | None = None
    mode: str = "night"
    place: str | None = None


@dataclass
class Interval:
    """A stretch of time; `end` is None while it lasts."""

    start: float
    end: float | None = None


def _overlap(start: float, end: float, since: float, until: float) -> float:
    return max(0.0, min(end, until) - max(start, since))


class SleepLog:
    """Records when the child slept, woke and cried."""

    def __init__(self) -> None:
        """Start empty."""
        self.sessions: list[SleepSession] = []
        self.wakeups: list[float] = []
        self.crying: list[Interval] = []

    @property
    def current(self) -> SleepSession | None:
        """The open sleep session, if the child is asleep."""
        if self.sessions and self.sessions[-1].end is None:
            return self.sessions[-1]
        return None

    def on_state(
        self, previous: ChildState, new: ChildState, now: float, *, mode: str, place: str | None
    ) -> None:
        """Update the log for a state change."""
        if new is ChildState.CRYING and previous is not ChildState.CRYING:
            self.crying.append(Interval(now))
            del self.crying[:-MAX_INTERVALS]
        elif previous is ChildState.CRYING and new is not ChildState.CRYING:
            if self.crying and self.crying[-1].end is None:
                self.crying[-1].end = now

        if new is ChildState.ASLEEP and self.current is None:
            last = self.sessions[-1] if self.sessions else None
            if last is not None and last.end is not None and now - last.end < MERGE_GAP_S:
                last.end = None
            else:
                self.sessions.append(SleepSession(start=now, mode=mode, place=place))
                del self.sessions[:-MAX_SESSIONS]
        elif new in _ENDS_SLEEP and self.current is not None:
            self.current.end = now
            if previous in _SLEEPING and new in (ChildState.AWAKE, ChildState.CRYING):
                self.wakeups.append(now)
                del self.wakeups[:-MAX_INTERVALS]

    def asleep_since(self) -> float | None:
        """Start of the open session."""
        return self.current.start if self.current else None

    def slept_between(self, since: float, until: float) -> float:
        """Seconds asleep within the window."""
        return sum(
            _overlap(session.start, session.end if session.end is not None else until, since, until)
            for session in self.sessions
        )

    def cried_between(self, since: float, until: float) -> float:
        """Seconds of crying within the window."""
        return sum(
            _overlap(interval.start, interval.end if interval.end is not None else until, since, until)
            for interval in self.crying
        )

    def wakeups_between(self, since: float, until: float) -> int:
        """Number of times the child woke within the window."""
        return sum(1 for moment in self.wakeups if since <= moment <= until)

    def last_session_seconds(self) -> float | None:
        """Length of the most recent finished session."""
        for session in reversed(self.sessions):
            if session.end is not None:
                return session.end - session.start
        return None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable copy."""
        return {
            "sessions": [
                {"start": s.start, "end": s.end, "mode": s.mode, "place": s.place} for s in self.sessions
            ],
            "wakeups": list(self.wakeups),
            "crying": [[interval.start, interval.end] for interval in self.crying],
        }

    def restore(self, raw: dict[str, Any] | None) -> None:
        """Take over stored data; malformed entries are dropped."""
        if not raw:
            return
        for item in raw.get("sessions", []):
            try:
                end = item.get("end")
                self.sessions.append(
                    SleepSession(
                        start=float(item["start"]),
                        end=None if end is None else float(end),
                        mode=str(item.get("mode", "night")),
                        place=item.get("place"),
                    )
                )
            except (KeyError, TypeError, ValueError, AttributeError):
                continue
        for moment in raw.get("wakeups", []):
            try:
                self.wakeups.append(float(moment))
            except (TypeError, ValueError):
                continue
        for interval in raw.get("crying", []):
            try:
                start, end = interval
                self.crying.append(Interval(float(start), None if end is None else float(end)))
            except (TypeError, ValueError):
                continue
