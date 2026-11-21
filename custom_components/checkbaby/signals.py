"""Latest raw signals with the time they changed. Pure, no Home Assistant imports."""

from __future__ import annotations

from dataclasses import dataclass, field

# The learned noise floor follows the level with this time constant.
BASELINE_TAU_S = 600.0
# Noise that lasts this long without crying is treated as the room's own sound.
AMBIENT_AFTER_S = 300.0
# Readings older than this no longer count as a valid vital signal.
VITAL_STALE_S = 15.0
# A level that has not moved at all for this long means a dead microphone.
FLAT_LEVEL_S = 600.0
# After the door closes, a caregiver is still assumed present this long.
CAREGIVER_LINGER_S = 20.0


@dataclass
class Flag:
    """A boolean signal that remembers since when it has its current value."""

    active: bool = False
    since: float = 0.0
    updated: float | None = None

    def set(self, active: bool, now: float) -> None:
        """Record the value; `since` only moves when the value changes."""
        if self.updated is None or active != self.active:
            self.since = now
        self.active = active
        self.updated = now

    def active_for(self, now: float) -> float:
        """Seconds the flag has been on, 0 if it is off."""
        return max(0.0, now - self.since) if self.active else 0.0

    def inactive_for(self, now: float) -> float:
        """Seconds the flag has been off; infinite if it was never reported."""
        if self.updated is None:
            return float("inf")
        return 0.0 if self.active else max(0.0, now - self.since)


@dataclass
class VitalReading:
    """One vital source: does it see breathing movement or body movement?"""

    valid: bool = False
    breathing: bool = False
    moving: bool = False
    rate: float | None = None
    updated: float | None = None
    last_breathing: float | None = None
    valid_since: float | None = None

    def usable(self, now: float) -> bool:
        """Valid and fresh."""
        return self.valid and self.updated is not None and now - self.updated <= VITAL_STALE_S

    def quiet_for(self, now: float, last_gross: float | None) -> float | None:
        """Seconds without breathing movement, after breathing had been seen.

        None when the source cannot make that statement: it is not usable, it
        has not seen the child breathe, or the last sign of life was a large
        movement. Silence after a large movement usually means the child was
        lifted out, and it cannot be told apart from anything worse, so it is
        never counted. The source has to see breathing again first.
        """
        if not self.usable(now) or self.last_breathing is None or self.valid_since is None:
            return None
        if last_gross is not None and last_gross >= self.last_breathing:
            return None
        if self.breathing or self.moving:
            return 0.0
        return now - max(self.last_breathing, self.valid_since)


@dataclass
class Signals:
    """Everything the sources reported, for the active sleep place."""

    crying: Flag = field(default_factory=Flag)
    scream: Flag = field(default_factory=Flag)
    motion: Flag = field(default_factory=Flag)
    loud: Flag = field(default_factory=Flag)
    door_open: Flag = field(default_factory=Flag)
    person: Flag = field(default_factory=Flag)
    pet_in_bed: Flag = field(default_factory=Flag)
    smoke: Flag = field(default_factory=Flag)
    presence: bool | None = None
    internet: bool | None = None
    temperature: float | None = None
    humidity: float | None = None
    level_db: float | None = None
    level_updated: float | None = None
    level_changed: float | None = None
    baseline_db: float | None = None
    # A level read from another entity may legitimately stay constant.
    flat_detection: bool = True
    # When the camera or a vital source last saw a large movement.
    last_gross: float | None = None
    vitals: dict[str, VitalReading] = field(default_factory=dict[str, VitalReading])

    def set_level(self, level_db: float, margin_db: float, now: float) -> None:
        """Record a sound level, learn the noise floor and derive `loud`."""
        if self.level_db is None or abs(level_db - self.level_db) > 0.01:
            self.level_changed = now
        previous = self.level_updated
        self.level_db = level_db
        self.level_updated = now
        if self.baseline_db is None:
            self.baseline_db = level_db
        is_loud = level_db > self.baseline_db + margin_db
        self.loud.set(is_loud, now)
        # Learn the floor from quiet moments, so crying does not raise it. Noise
        # that simply stays, without any crying, is the room (a white-noise
        # machine, a humidifier): after a while the floor follows it up.
        ambient = not is_loud or self.loud.active_for(now) >= AMBIENT_AFTER_S
        if ambient and not self.crying.active and not self.scream.active:
            elapsed = 1.0 if previous is None else min(60.0, max(0.0, now - previous))
            alpha = min(1.0, elapsed / BASELINE_TAU_S)
            self.baseline_db += alpha * (level_db - self.baseline_db)

    def microphone_flat(self, now: float) -> bool:
        """True when levels still arrive but have not moved for a long time."""
        return (
            self.flat_detection
            and self.level_changed is not None
            and self.level_updated is not None
            and now - self.level_changed >= FLAT_LEVEL_S
            and now - self.level_updated < FLAT_LEVEL_S
        )

    def set_vital(
        self,
        source: str,
        *,
        valid: bool,
        breathing: bool,
        moving: bool,
        rate: float | None,
        now: float,
    ) -> None:
        """Record a vital reading and when the source last saw a sign of life."""
        reading = self.vitals.setdefault(source, VitalReading())
        if valid and not reading.valid:
            reading.valid_since = now
        if not valid:
            reading.valid_since = None
        reading.valid = valid
        reading.breathing = valid and breathing
        reading.moving = valid and moving
        reading.rate = rate if valid and breathing else None
        reading.updated = now
        if reading.breathing:
            reading.last_breathing = now
        if reading.moving:
            self.last_gross = now

    def forget_breathing(self) -> None:
        """Someone was with the child: every source has to see breathing anew."""
        for reading in self.vitals.values():
            reading.last_breathing = None

    def caregiver_present(self, now: float) -> bool:
        """Someone is with the child: door open (or just closed) or a person seen."""
        if self.door_open.active or self.person.active:
            return True
        return (
            self.door_open.inactive_for(now) < CAREGIVER_LINGER_S
            or self.person.inactive_for(now) < CAREGIVER_LINGER_S
        )

    def distress(self, cry_confirm_s: float, scream_confirm_s: float, now: float) -> bool:
        """Crying or screaming long enough to count."""
        crying = self.crying.active and self.crying.active_for(now) >= cry_confirm_s
        screaming = self.scream.active and self.scream.active_for(now) >= scream_confirm_s
        return crying or screaming

    def distress_for(self, now: float) -> float:
        """Seconds of uninterrupted crying or screaming."""
        return max(self.crying.active_for(now), self.scream.active_for(now))

    def distress_quiet_for(self, now: float) -> float:
        """Seconds since both crying and screaming stopped."""
        return min(self.crying.inactive_for(now), self.scream.inactive_for(now))

    def activity(self) -> bool:
        """Movement or noise right now."""
        return self.motion.active or self.loud.active

    def calm_for(self, now: float) -> float:
        """Seconds without movement and without noise."""
        return min(self.motion.inactive_for(now), self.loud.inactive_for(now))

    def activity_for(self, now: float) -> float:
        """Seconds of uninterrupted movement or noise."""
        return max(self.motion.active_for(now), self.loud.active_for(now))
