"""Breathing-movement hint: pure signal processing (numpy only, no I/O).

Feed grayscale ROI frames with timestamps into :class:`BreathingAnalyzer` and
ask it for a :class:`Result` about once per second.

The one property everything else is built around: missing or bad data is
reported as ``unusable`` and never as ``no_motion``. ``no_motion`` is only
produced from a contiguous run of valid frames that is long enough to judge.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import StrEnum
from typing import NamedTuple

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]


class Status(StrEnum):
    """Wire contract: these strings are published over MQTT."""

    PERIODIC = "periodic"
    GROSS_MOTION = "gross_motion"
    NO_MOTION = "no_motion"
    UNUSABLE = "unusable"


@dataclass(frozen=True)
class SignalConfig:
    """Thresholds. The defaults are tuned on synthetic data only."""

    window_s: float = 25.0  # longest stretch of frames that is analysed
    min_window_s: float = 12.0  # shortest contiguous stretch that may be judged
    band_low_hz: float = 0.3  # 18 breaths/min
    band_high_hz: float = 1.5  # 90 breaths/min
    min_fps: float = 4.0  # effective frame rate needed inside the stretch
    max_gap_s: float = 1.0  # a longer gap between frames restarts the analysis
    stale_after_s: float = 2.0  # newest frame older than this: unusable
    frozen_after_s: float = 5.0  # identical frames for this long: unusable
    periodic_confidence: float = 0.3  # share of in-band power in the peak above the noise floor
    peak_halfwidth_hz: float = 0.1  # tolerated wobble of the breathing rate
    min_amplitude: float = 0.02  # periodic component, % of mean brightness (RMS)
    gross_motion_threshold: float = 3.0  # block change over motion_lag_s, % of mean brightness
    motion_lag_s: float = 0.5
    dark_level: float = 16.0  # mean grey level (0..255) below this: too dark
    saturated_level: float = 250.0
    max_saturated_fraction: float = 0.25
    min_contrast: float = 3.0  # spread of block brightness, % of mean brightness
    max_noise: float = 0.08  # pixel noise sigma / mean brightness
    grid: int = 8  # blocks per axis


@dataclass(frozen=True)
class Result:
    status: Status
    rate: float | None  # breaths per minute, only when status is periodic
    confidence: float  # 0..1
    motion: float  # gross motion measure of the newest frame, % of mean brightness
    reason: str  # short cause for logs; not part of the MQTT contract


class Periodicity(NamedTuple):
    rate: float  # breaths per minute of the dominant in-band component
    confidence: float  # share of in-band power in that component above the noise floor, 0..1
    amplitude: float  # RMS of that component, in units of the input signal


class _Sample(NamedTuple):
    ts: float
    features: FloatArray
    motion: float
    gross: bool


_NOT_PERIODIC = Periodicity(0.0, 0.0, 0.0)


def estimate_periodicity(
    timestamps: npt.ArrayLike,
    signals: npt.ArrayLike,
    config: SignalConfig = SignalConfig(),
) -> Periodicity:
    """Dominant frequency in the breathing band of one or more motion signals.

    ``signals`` is one value per timestamp, or one row per timestamp with a
    column per signal (for example per image block). The power spectra of the
    columns are averaged, so columns that move in opposite directions do not
    cancel and the noise floor becomes smooth.
    """
    t = np.asarray(timestamps, dtype=np.float64)
    x = np.asarray(signals, dtype=np.float64)
    if x.ndim == 1:
        x = x[:, None]
    n = t.size
    if n < 8 or x.shape[0] != n or not np.all(np.diff(t) > 0) or not np.all(np.isfinite(x)):
        return _NOT_PERIODIC
    span = float(t[-1] - t[0])
    grid = np.linspace(t[0], t[-1], n)
    u = np.column_stack([np.interp(grid, t, column) for column in x.T])
    ramp = np.linspace(-1.0, 1.0, n)[:, None]
    u = u - u.mean(axis=0)
    u = u - ramp * (ramp * u).sum(axis=0) / float((ramp * ramp).sum())
    window = np.hanning(n)[:, None]
    spectrum = np.abs(np.fft.rfft(u * window, axis=0)) ** 2
    # Scaled so that the bins of a sinusoid add up to its variance.
    power = 2.0 * spectrum.mean(axis=1) / (n * float((window * window).sum()))
    freqs = np.fft.rfftfreq(n, d=span / (n - 1))
    band = np.flatnonzero((freqs >= config.band_low_hz) & (freqs <= config.band_high_hz))
    if band.size < 3:
        return _NOT_PERIODIC
    band_power = float(power[band].sum())
    k = int(band[np.argmax(power[band])])
    if band_power <= 0.0:
        return _NOT_PERIODIC
    # A stronger neighbour outside the band means the in-band maximum is only
    # leakage from an out-of-band component (slow drift, flicker, a fan).
    if power[k - 1] > power[k] or (k + 1 < power.size and power[k + 1] > power[k]):
        return _NOT_PERIODIC
    half = max(2, int(np.ceil(config.peak_halfwidth_hz * span)))
    peak_bins = band[(band >= k - half) & (band <= k + half)]
    peak = float(power[peak_bins].sum())
    freq = float((freqs[peak_bins] * power[peak_bins]).sum()) / peak
    # Only what stands out above the noise floor counts; the median bin is the floor.
    excess = max(0.0, peak - peak_bins.size * float(np.median(power[band])))
    return Periodicity(60.0 * freq, min(1.0, excess / band_power), float(np.sqrt(excess)))


def _measure(frame: FloatArray, config: SignalConfig) -> tuple[FloatArray | None, float, str]:
    """Return (block features, expected noise in the motion measure, fault).

    Features are block brightness in percent of the frame's mean brightness,
    which removes exposure and lighting changes that hit the whole ROI.
    """
    if not np.all(np.isfinite(frame)):
        return None, 0.0, "invalid_frame"
    mean = float(frame.mean())
    if mean < config.dark_level:
        return None, 0.0, "too_dark"
    if float((frame >= config.saturated_level).mean()) > config.max_saturated_fraction:
        return None, 0.0, "saturated"
    height, width = frame.shape
    noise = 0.0
    if height >= 3 and width >= 3:
        # Median of a Laplacian-like filter: responds to pixel noise, hardly to
        # image structure. For white noise of sigma s the filter output has
        # sigma 6 s.
        laplace = (
            4.0 * frame[1:-1, 1:-1]
            - 2.0 * (frame[:-2, 1:-1] + frame[2:, 1:-1] + frame[1:-1, :-2] + frame[1:-1, 2:])
            + (frame[:-2, :-2] + frame[:-2, 2:] + frame[2:, :-2] + frame[2:, 2:])
        )
        noise = 1.4826 * float(np.median(np.abs(laplace))) / 6.0 / mean
    if noise > config.max_noise:
        return None, 0.0, "too_noisy"
    rows = np.linspace(0, height, min(config.grid, height) + 1).astype(np.intp)
    cols = np.linspace(0, width, min(config.grid, width) + 1).astype(np.intp)
    sums = np.add.reduceat(np.add.reduceat(frame, rows[:-1], axis=0), cols[:-1], axis=1)
    areas = np.outer(np.diff(rows), np.diff(cols))
    features = (100.0 / mean) * (sums / areas).ravel()
    if float(features.std()) < config.min_contrast:
        # Nothing in the picture that could show a movement (lens covered,
        # blank wall, fog of noise): absence of motion would mean nothing.
        return None, 0.0, "low_contrast"
    # Mean absolute difference of two block means that differ only by noise.
    noise_motion = 100.0 * noise * 2.0 / float(np.sqrt(np.pi * areas.mean()))
    return features, noise_motion, ""


class BreathingAnalyzer:
    """Sliding-window analysis of ROI frames. Not thread-safe."""

    def __init__(self, config: SignalConfig | None = None) -> None:
        self.config = config or SignalConfig()
        self._samples: deque[_Sample] = deque()
        self._last_ts: float | None = None
        self._fault = ""
        self._previous: FloatArray | None = None
        self._same_since: float | None = None

    def reset(self) -> None:
        self._samples.clear()
        self._last_ts = self._previous = self._same_since = None
        self._fault = ""

    def add_frame(self, ts: float, frame: npt.ArrayLike) -> None:
        """Add one grayscale frame (2-D, grey levels 0..255) taken at ``ts`` seconds."""
        image = np.asarray(frame, dtype=np.float64)
        if image.ndim != 2 or image.size == 0:
            raise ValueError("frame must be a non-empty 2-D grayscale array")
        cfg = self.config
        last, self._last_ts = self._last_ts, ts
        if last is not None and not 0.0 < ts - last <= cfg.max_gap_s:
            # Gap, duplicate or clock jump: never bridge it.
            self._samples.clear()
            self._previous = self._same_since = None
        features, noise_motion, self._fault = _measure(image, cfg)
        if features is not None:
            # A live sensor always has some noise. Frames that stay identical
            # mean a frozen picture, which says nothing about the child.
            if self._previous is None or not np.array_equal(features, self._previous):
                self._same_since = None
            elif self._same_since is None:
                self._same_since = last
            self._previous = features
            if self._same_since is not None and ts - self._same_since >= cfg.frozen_after_s:
                features, self._fault = None, "frozen"
        if features is None:
            self._samples.clear()
            return
        if self._samples and self._samples[-1].features.shape != features.shape:
            self._samples.clear()
        motion = 0.0
        if self._samples:
            reference = self._samples[0]
            for sample in reversed(self._samples):
                if sample.ts <= ts - cfg.motion_lag_s:
                    reference = sample
                    break
            motion = float(np.abs(features - reference.features).mean())
        gross = motion > max(cfg.gross_motion_threshold, 5.0 * noise_motion)
        self._samples.append(_Sample(ts, features, motion, gross))
        while self._samples[0].ts < ts - cfg.window_s:
            self._samples.popleft()

    def evaluate(self, now: float) -> Result:
        """Judge the frames seen so far, as of ``now`` (same clock as the frames)."""
        cfg = self.config
        if self._last_ts is None:
            return _unusable("no_frames")
        if not abs(now - self._last_ts) <= cfg.stale_after_s:
            return _unusable("stale")
        if self._fault or not self._samples:
            return _unusable(self._fault or "no_frames")
        samples = list(self._samples)
        motion = samples[-1].motion
        last_gross = max((i for i, s in enumerate(samples) if s.gross), default=-1)
        run = samples[last_gross + 1 :]
        if not run or run[-1].ts - run[0].ts < cfg.min_window_s:
            if last_gross >= 0:
                # Moving, or settled so recently that breathing cannot be judged yet.
                return Result(Status.GROSS_MOTION, None, 0.0, motion, "gross_motion")
            return _unusable("insufficient_data")
        ts = np.array([s.ts for s in run])
        gaps = np.diff(ts)
        span = float(ts[-1] - ts[0])
        undersampled = float(gaps[gaps > 0.5 / cfg.band_high_hz].sum())
        if (ts.size - 1) / span < cfg.min_fps or undersampled > 0.1 * span:
            return _unusable("irregular_timestamps")
        found = estimate_periodicity(ts, np.stack([s.features for s in run]), cfg)
        if found.confidence >= cfg.periodic_confidence and found.amplitude >= cfg.min_amplitude:
            return Result(Status.PERIODIC, found.rate, found.confidence, motion, "periodic")
        return Result(Status.NO_MOTION, None, found.confidence, motion, "no_motion")


def _unusable(reason: str) -> Result:
    return Result(Status.UNUSABLE, None, 0.0, 0.0, reason)
