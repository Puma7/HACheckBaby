"""Night report and quick check summaries. Pure, no Home Assistant imports."""

from __future__ import annotations

from typing import Any

from .monitor import Snapshot
from .sleep_log import SleepLog
from .texts import alert_message, problem_names, state_name, text
from .types import AlertLevel


def night_report(log: SleepLog, since: float, now: float) -> dict[str, Any]:
    """Numbers for the time since `since` (usually the evening before)."""
    stretches = [
        min(session.end if session.end is not None else now, now) - max(session.start, since)
        for session in log.sessions
        if (session.end is None or session.end > since) and session.start < now
    ]
    return {
        "since": since,
        "until": now,
        "slept_seconds": round(log.slept_between(since, now)),
        "cried_seconds": round(log.cried_between(since, now)),
        "wakeups": log.wakeups_between(since, now),
        "sleep_phases": len(stretches),
        "longest_stretch_seconds": round(max(stretches, default=0.0)),
    }


def night_report_text(language: str, child: str, report: dict[str, Any]) -> str:
    """The night report as one sentence."""
    slept = int(report["slept_seconds"])
    if slept <= 0:
        return text(language, "report_none", child=child)
    return text(
        language,
        "report",
        child=child,
        hours=slept // 3600,
        minutes=(slept % 3600) // 60,
        wakeups=report["wakeups"],
        cried=round(int(report["cried_seconds"]) / 60),
        longest=round(int(report["longest_stretch_seconds"]) / 60),
    )


def quick_check_text(language: str, child: str, snapshot: Snapshot, now: float) -> str:
    """How is the child, in one or two sentences."""
    parts = [text(language, "quick", child=child, state=state_name(language, snapshot.state))]
    if snapshot.alert_kind is not None and snapshot.level >= AlertLevel.WARNING:
        alert = alert_message(language, child, snapshot.alert_kind, snapshot.level, snapshot.alert_detail)
        parts.append(text(language, "quick_alert", alert=alert.rstrip(".")))
    if snapshot.asleep_since is not None:
        parts.append(text(language, "quick_asleep", minutes=round((now - snapshot.asleep_since) / 60)))
    if snapshot.assessment is not None and snapshot.assessment.reason:
        parts.append(text(language, "quick_ai", reason=snapshot.assessment.reason))
    if snapshot.problems:
        parts.append(text(language, "quick_problems", problems=problem_names(language, snapshot.problems)))
    return "".join(parts)
