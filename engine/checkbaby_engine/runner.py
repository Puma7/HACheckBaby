"""The engine loop: frames in, a status out about once per second."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

from .capture import FrameSource
from .publisher import Publisher
from .signal import BreathingAnalyzer, Result

_LOGGER = logging.getLogger(__name__)


class Engine:
    def __init__(
        self,
        source: FrameSource,
        analyzer: BreathingAnalyzer,
        publisher: Publisher,
        *,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
        eval_interval_s: float = 1.0,
        read_timeout_s: float = 0.25,
    ) -> None:
        self._source = source
        self._analyzer = analyzer
        self._publisher = publisher
        self._clock = clock
        self._sleep = sleep
        self._eval_interval_s = eval_interval_s
        self._read_timeout_s = read_timeout_s
        self._last_eval: float | None = None
        self._last_result: Result | None = None
        self._source_failed = False

    def step(self) -> None:
        """Take at most one frame, then evaluate and publish if it is time.

        A source that fails or delivers nothing must not stop the reporting:
        the analyzer answers ``unusable`` as soon as its newest frame is stale.
        """
        try:
            frame = self._source.read(self._read_timeout_s)
            if frame is not None:
                self._analyzer.add_frame(frame.ts, frame.image)
            if self._source_failed:
                _LOGGER.info("frame source recovered")
                self._source_failed = False
        except Exception as err:
            if not self._source_failed:  # log once, not on every retry
                _LOGGER.warning("frame source failed: %s", type(err).__name__)
                self._source_failed = True
            self._sleep(self._read_timeout_s)
        now = self._clock()
        if self._last_eval is not None and 0.0 <= now - self._last_eval < self._eval_interval_s:
            return
        self._last_eval = now
        result = self._analyzer.evaluate(now)
        previous = self._last_result
        if previous is None or (previous.status, previous.reason) != (result.status, result.reason):
            _LOGGER.info("status %s (%s)", result.status.value, result.reason)
        self._last_result = result
        self._publisher.update(result, now)

    def run(self, stop: threading.Event) -> None:
        """Run until ``stop`` is set; always ends with ``offline``."""
        self._publisher.start()
        try:
            while not stop.is_set():
                self.step()
        finally:
            try:
                self._source.close()
            finally:
                self._publisher.stop()
