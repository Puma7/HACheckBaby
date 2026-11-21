"""Frame sources: an RTSP reader built on PyAV and a synthetic scene for tests."""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np
import numpy.typing as npt

from .config import Roi, mask_url, redact

_LOGGER = logging.getLogger(__name__)

Image = npt.NDArray[np.float32]


@dataclass(frozen=True)
class Frame:
    ts: float  # unix epoch seconds
    image: Image  # grayscale ROI, grey levels 0..255


class FrameSource(Protocol):
    def read(self, timeout: float) -> Frame | None:
        """Return the next frame, or None if none arrived within ``timeout`` seconds."""
        ...

    def close(self) -> None: ...


def crop_and_downsize(gray: npt.NDArray[Any], roi: Roi, width: int) -> Image:
    """Cut the ROI (fractions of the picture) and shrink it by averaging whole pixels.

    The shrink factor is an integer, so the result is at least ``width`` wide.
    Averaging keeps the sub-pixel brightness changes the analysis lives on.
    """
    height_px, width_px = gray.shape
    x0 = min(int(roi.x * width_px), width_px - 1)
    y0 = min(int(roi.y * height_px), height_px - 1)
    x1 = max(x0 + 1, min(width_px, round((roi.x + roi.w) * width_px)))
    y1 = max(y0 + 1, min(height_px, round((roi.y + roi.h) * height_px)))
    crop = gray[y0:y1, x0:x1]
    k = max(1, min(crop.shape[1] // max(1, width), crop.shape[0]))
    rows, cols = crop.shape[0] // k, crop.shape[1] // k
    blocks = crop[: rows * k, : cols * k].reshape(rows, k, cols, k)
    return np.asarray(blocks.mean(axis=(1, 3), dtype=np.float32), dtype=np.float32)


def _open_av(url: str) -> Any:
    import av  # imported here so that tests and the synthetic source need no PyAV

    options = {"rtsp_transport": "tcp"} if url.startswith(("rtsp://", "rtsps://")) else {}
    # (open timeout, read timeout) in seconds; a stalled stream raises instead of hanging.
    return av.open(url, options=options, timeout=(10.0, 5.0))


class RtspSource:
    """Decodes a stream in a background thread and hands out ROI frames.

    Reconnects with exponential backoff. ``read`` never blocks longer than its
    timeout, so the caller can keep reporting while the stream is down.
    """

    def __init__(
        self,
        url: str,
        roi: Roi,
        fps: float,
        frame_width: int,
        *,
        opener: Callable[[str], Any] | None = None,
        clock: Callable[[], float] = time.time,
        backoff_s: tuple[float, float] = (1.0, 30.0),
    ) -> None:
        self._url = url
        self._roi = roi
        self._min_interval = 0.75 / fps
        self._frame_width = frame_width
        self._opener = opener or _open_av
        self._clock = clock
        self._backoff_s = backoff_s
        self._frames: queue.Queue[Frame] = queue.Queue(maxsize=64)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._anchor: float | None = None
        self._last_kept: float | None = None

    def read(self, timeout: float) -> Frame | None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="rtsp-reader", daemon=True)
            self._thread.start()
        try:
            return self._frames.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=7.0)

    def _run(self) -> None:
        delay = self._backoff_s[0]
        masked = mask_url(self._url)
        while not self._stop.is_set():
            try:
                container = self._opener(self._url)
                try:
                    _LOGGER.info("stream open: %s", masked)
                    self._anchor = None
                    for av_frame in container.decode(video=0):
                        if self._stop.is_set():
                            return
                        delay = self._backoff_s[0]
                        self._handle(av_frame)
                finally:
                    container.close()
                _LOGGER.warning("stream ended: %s", masked)
            except Exception as err:  # PyAV raises many unrelated error types
                # FFmpeg error texts can quote the URL including its password.
                _LOGGER.warning("stream error on %s: %s", masked, redact(str(err), self._url))
            if self._stop.wait(delay):
                return
            delay = min(delay * 2.0, self._backoff_s[1])

    def _handle(self, av_frame: Any) -> None:
        ts = self._timestamp(av_frame.time)
        if self._last_kept is not None and 0.0 <= ts - self._last_kept < self._min_interval:
            return  # drop to the target frame rate before the costly conversion
        self._last_kept = ts
        gray = av_frame.to_ndarray(format="gray")
        frame = Frame(ts, crop_and_downsize(gray, self._roi, self._frame_width))
        while True:
            try:
                self._frames.put_nowait(frame)
                return
            except queue.Full:  # consumer too slow: drop the oldest frame
                try:
                    self._frames.get_nowait()
                except queue.Empty:
                    pass

    def _timestamp(self, media_time: float | None) -> float:
        """Presentation time mapped onto the wall clock.

        Arrival times jitter with the network; presentation times do not. A
        frame can arrive late but never early, so the smallest offset seen is
        the true one: follow it down at once (this also collapses the burst of
        buffered frames after connecting) and up only slowly (clock drift).
        """
        now = self._clock()
        if media_time is None:
            return now
        offset = now - media_time
        if self._anchor is None or abs(offset - self._anchor) > 1.0:
            self._anchor = offset
        else:
            self._anchor = min(offset, self._anchor + 0.002 * (offset - self._anchor))
        return self._anchor + media_time


def _still(_t: float) -> float:
    return 0.0


def _unity(_t: float) -> float:
    return 1.0


@dataclass
class SyntheticSource:
    """A textured surface that shifts vertically by ``displacement(t)`` pixels.

    Used by the tests and by ``synthetic://`` URLs for trying the MQTT side
    without a camera. ``t`` is seconds since the first frame.
    """

    displacement: Callable[[float], float] = _still
    fps: float = 8.0
    duration_s: float = 60.0
    width: int = 64
    height: int = 48
    brightness: float = 110.0
    contrast: float = 35.0  # standard deviation of the texture in grey levels
    noise_sigma: float = 2.0
    gain: Callable[[float], float] = _unity  # brightness factor over time (lighting, exposure)
    start_ts: float = 1_700_000_000.0
    seed: int = 0
    realtime: bool = False  # pace read() with the wall clock, starting now
    _index: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)
        waves = 8
        wavelength = self._rng.uniform(8.0, 48.0, waves)
        angle = self._rng.uniform(0.0, 2.0 * np.pi, waves)
        self._kx = 2.0 * np.pi / wavelength * np.cos(angle)
        self._ky = 2.0 * np.pi / wavelength * np.sin(angle)
        self._phase = self._rng.uniform(0.0, 2.0 * np.pi, waves)
        self._y, self._x = np.mgrid[0 : self.height, 0 : self.width].astype(np.float64)
        if self.realtime:
            self.start_ts = time.time()

    def render(self, t: float) -> Image:
        """The frame at ``t`` seconds, as an 8-bit camera would deliver it."""
        y: npt.NDArray[np.float64] = self._y - self.displacement(t)
        pattern = np.zeros_like(y)
        for kx, ky, phase in zip(self._kx, self._ky, self._phase, strict=True):
            pattern += np.sin(kx * self._x + ky * y + phase)
        pattern *= np.sqrt(2.0 / self._kx.size)  # unit standard deviation
        image = self.gain(t) * (self.brightness + self.contrast * pattern)
        image += self._rng.normal(0.0, self.noise_sigma, image.shape)
        return np.clip(np.rint(image), 0.0, 255.0).astype(np.float32)

    def read(self, timeout: float = 0.0) -> Frame | None:
        t = self._index / self.fps
        if t > self.duration_s:
            if self.realtime:
                time.sleep(timeout)
            return None
        if self.realtime:
            wait = self.start_ts + t - time.time()
            if wait > timeout:
                time.sleep(timeout)
                return None
            time.sleep(max(0.0, wait))
        self._index += 1
        return Frame(self.start_ts + t, self.render(t))

    def close(self) -> None:
        return None
