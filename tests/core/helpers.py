"""A small harness that drives the monitor through time."""

from __future__ import annotations

from custom_components.checkbaby.alerts import Notification
from custom_components.checkbaby.monitor import Monitor
from custom_components.checkbaby.profiles import AgeProfile
from custom_components.checkbaby.settings import Settings
from custom_components.checkbaby.types import AlertKind, Stage

T0 = 1_800_000_000.0
AUDIO = "audio_level"


class Night:
    """A monitor with a clock. Sources report healthy unless a test stops them."""

    def __init__(self, *, profile: AgeProfile = AgeProfile.NEWBORN, armed: bool = True, **settings: object) -> None:
        self.now = T0
        self.profile = profile
        self.monitor = Monitor(Settings(armed=armed, **settings), self.now)  # type: ignore[arg-type]
        self.monitor.watchdog.expect(AUDIO, max_age_s=60.0, core=True)
        self.sent: list[Notification] = []
        self.audio_alive = True
        self.level_db = -50.0
        # A live microphone never reports exactly the same level twice.
        self.flat_microphone = False
        self._ticks = 0
        # Start from a known calm state.
        self.advance(2)

    def advance(self, seconds: float, step: float = 1.0) -> None:
        """Let time pass, ticking once per step."""
        end = self.now + seconds
        while self.now < end:
            self.now = min(end, self.now + step)
            if self.audio_alive:
                self.monitor.watchdog.seen(AUDIO, self.now)
                self._ticks += 1
                jitter = 0.0 if self.flat_microphone else (0.2 if self._ticks % 2 else -0.2)
                self.monitor.signals.set_level(
                    self.level_db + jitter, self.monitor.settings.noise_margin_db, self.now
                )
            self.monitor.tick(self.now, self.profile)
            self.sent.extend(self.monitor.drain_notifications())

    def cry(self, active: bool = True) -> None:
        self.monitor.signals.crying.set(active, self.now)

    def stages(self, kind: AlertKind) -> list[Stage]:
        """The notification stages sent for one alert kind, in order."""
        return [note.stage for note in self.sent if note.kind is kind]

    def pushes(self, kind: AlertKind) -> list[Notification]:
        """Notifications that reach a phone (not clears or acknowledgements)."""
        loud = (Stage.FIRST, Stage.UPGRADE, Stage.REPEAT, Stage.ESCALATE)
        return [note for note in self.sent if note.kind is kind and note.stage in loud]
