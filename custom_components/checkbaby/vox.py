"""Voice-activated audio relay: open on noise, close after quiet. Pure."""

from __future__ import annotations

from enum import StrEnum


class VoxAction(StrEnum):
    """What the audio relay should do now."""

    START = "start"
    STOP = "stop"


class VoxController:
    """Decides when the child's room audio plays on the parents' speaker."""

    def __init__(self, open_after_s: float = 2.0, close_after_s: float = 60.0) -> None:
        """Open after a short confirmation, close after a longer quiet period."""
        self._open_after_s = open_after_s
        self._close_after_s = close_after_s
        self.playing = False

    def update(self, *, enabled: bool, noise_for: float, quiet_for: float) -> VoxAction | None:
        """Return an action when the relay should change, else None."""
        if self.playing and (not enabled or quiet_for >= self._close_after_s):
            self.playing = False
            return VoxAction.STOP
        if not self.playing and enabled and noise_for >= self._open_after_s:
            self.playing = True
            return VoxAction.START
        return None
