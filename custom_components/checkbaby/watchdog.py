"""Heartbeat of every source. Pure, no Home Assistant imports.

A monitor that fails silently is worse than none: every source that is
expected but stale or unhealthy becomes a named problem.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _Source:
    max_age_s: float | None
    last_seen: float | None = None
    healthy: bool | None = None
    core: bool = False


class Watchdog:
    """Tracks freshness and health of the expected sources."""

    def __init__(self, started: float, grace_s: float = 120.0) -> None:
        """Start with a grace period in which missing sources are not problems yet."""
        self._started = started
        self._grace_s = grace_s
        self._sources: dict[str, _Source] = {}

    def expect(self, name: str, *, max_age_s: float | None = None, core: bool = False) -> None:
        """Declare a source. With max_age_s it must report regularly."""
        existing = self._sources.get(name)
        if existing is None:
            self._sources[name] = _Source(max_age_s=max_age_s, core=core)
        else:
            existing.max_age_s = max_age_s
            existing.core = core

    def forget(self, name: str) -> None:
        """Stop expecting a source."""
        self._sources.pop(name, None)

    def restart_grace(self, now: float) -> None:
        """Begin a new grace period, e.g. after the sleep place changed."""
        self._started = now
        for source in self._sources.values():
            source.last_seen = None
            source.healthy = None

    def seen(self, name: str, now: float) -> None:
        """A source reported something."""
        source = self._sources.get(name)
        if source is not None:
            source.last_seen = now

    def set_healthy(self, name: str, healthy: bool, now: float) -> None:
        """A source reported its own health."""
        source = self._sources.get(name)
        if source is not None:
            source.healthy = healthy
            source.last_seen = now

    def in_grace(self, now: float) -> bool:
        """True right after start, while sources may not have reported yet."""
        return now - self._started < self._grace_s

    def _is_problem(self, source: _Source, now: float) -> bool:
        if source.healthy is False:
            return True
        if source.max_age_s is None:
            # Health-only source: silence after the grace period is a problem.
            return source.healthy is None and not self.in_grace(now)
        if source.last_seen is None:
            return not self.in_grace(now)
        return now - source.last_seen > source.max_age_s

    def problems(self, now: float) -> list[str]:
        """Names of all sources that are unhealthy, stale or missing."""
        return sorted(name for name, source in self._sources.items() if self._is_problem(source, now))

    def usable(self, now: float) -> bool:
        """False when a core source is a problem: the child's state is unknown then."""
        return not any(source.core and self._is_problem(source, now) for source in self._sources.values())
