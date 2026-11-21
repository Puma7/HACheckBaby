"""Signal processing against synthetic scenes.

The property tested hardest: bad or missing data gives ``unusable`` and never
``no_motion``.
"""

from __future__ import annotations

import math
from functools import partial

import numpy as np
import pytest
from helpers import analyze, breathing, check_invariants, statuses

from checkbaby_engine.capture import SyntheticSource
from checkbaby_engine.signal import (
    BreathingAnalyzer,
    SignalConfig,
    Status,
    estimate_periodicity,
)

CFG = SignalConfig()
READY = CFG.min_window_s + 1.0  # first evaluation that has enough data
# A breathing rate of 0 is a chest that does not move.
STILL_OR_BREATHING = pytest.mark.parametrize("bpm", [0.0, 40.0], ids=["still", "breathing"])


def test_status_strings_are_the_wire_contract() -> None:
    assert {s.value for s in Status} == {"periodic", "gross_motion", "no_motion", "unusable"}
    assert f"{Status.NO_MOTION}" == "no_motion"  # formats as the bare string


# --- periodic -----------------------------------------------------------------


@pytest.mark.parametrize("fps", [5.0, 8.0, 10.0])
@pytest.mark.parametrize("bpm", [20.0, 30.0, 40.0, 60.0, 80.0])
def test_breathing_rate_is_found(bpm: float, fps: float) -> None:
    results = analyze(SyntheticSource(breathing(bpm), fps=fps, duration_s=45.0, seed=int(bpm)))
    assert statuses(results, end=CFG.min_window_s - 1.0) == {"unusable"}
    ready = [r for t, r in results if t >= READY]
    assert len(ready) >= 30
    for result in ready:
        assert result.status is Status.PERIODIC
        assert result.rate == pytest.approx(bpm, abs=3.0)
        assert result.confidence >= CFG.periodic_confidence


@pytest.mark.parametrize("seed", range(4))
@pytest.mark.parametrize(
    ("amplitude", "noise_sigma"),
    [(0.3, 5.0), (0.15, 3.0), (0.1, 2.0)],  # pixels of shift, grey levels of sensor noise
)
@pytest.mark.parametrize("bpm", [20.0, 40.0, 60.0])
def test_breathing_rate_is_found_in_noise(bpm: float, amplitude: float, noise_sigma: float, seed: int) -> None:
    source = SyntheticSource(
        breathing(bpm, amplitude), duration_s=40.0, noise_sigma=noise_sigma, seed=seed
    )
    for t, result in analyze(source):
        if t >= READY:
            assert result.status is Status.PERIODIC
            assert result.rate == pytest.approx(bpm, abs=3.0)


def test_breathing_with_a_wandering_rate_stays_periodic() -> None:
    # 36/min wandering by +-3.6/min over 20 s, as real breathing does.
    def chest(t: float) -> float:
        wander = 0.06 / (2.0 * math.pi * 0.05) * math.sin(2.0 * math.pi * 0.05 * t)
        return 0.3 * math.sin(2.0 * math.pi * (0.6 * t + wander))

    for t, result in analyze(SyntheticSource(chest, duration_s=80.0)):
        if t >= READY:
            assert result.status is Status.PERIODIC
            assert result.rate == pytest.approx(36.0, abs=4.0)


@pytest.mark.parametrize("noise_sigma", [1.0, 5.0])
def test_sensor_noise_alone_is_never_breathing(noise_sigma: float) -> None:
    worst = 0.0
    for seed in range(20):
        results = analyze(SyntheticSource(duration_s=40.0, noise_sigma=noise_sigma, seed=seed))
        assert statuses(results, start=READY) == {"no_motion"}
        worst = max(worst, max(r.confidence for _, r in results))
    # Not just below the threshold but far below it.
    assert worst < 0.5 * CFG.periodic_confidence


# --- breathing stops ----------------------------------------------------------


@pytest.mark.parametrize("noise_sigma", [1.0, 3.0])
@pytest.mark.parametrize("bpm", [20.0, 40.0, 60.0])
def test_breathing_that_stops_becomes_no_motion_within_the_window(bpm: float, noise_sigma: float) -> None:
    stop = 40.0
    chest = breathing(bpm)
    source = SyntheticSource(
        lambda t: chest(min(t, stop)), duration_s=90.0, noise_sigma=noise_sigma, seed=int(bpm)
    )
    results = analyze(source)
    assert statuses(results, start=READY, end=stop) == {"periodic"}
    first_still = min(t for t, r in results if r.status is Status.NO_MOTION)
    assert stop < first_still <= stop + CFG.window_s + 3.0
    assert statuses(results, start=first_still) == {"no_motion"}
    # The data stayed valid throughout, so nothing else may show up.
    assert statuses(results, start=READY) == {"periodic", "no_motion"}


# --- gross motion -------------------------------------------------------------


def _thrash(start: float, end: float, bpm: float = 36.0) -> SyntheticSource:
    """Breathing, large random movement between ``start`` and ``end``, breathing again."""
    fps = 8.0
    walk = np.cumsum(np.random.default_rng(1).normal(0.0, 3.0, int(end * fps) + 2))
    chest = breathing(bpm)

    def position(t: float) -> float:
        if start <= t < end:
            return float(walk[int(t * fps)])
        return chest(t) + (float(walk[int(end * fps)]) if t >= end else 0.0)

    return SyntheticSource(position, fps=fps, duration_s=80.0)


def test_gross_motion_is_reported_at_once_and_breathing_returns() -> None:
    results = analyze(_thrash(30.0, 40.0))
    assert statuses(results, start=READY, end=29.0) == {"periodic"}
    assert statuses(results, start=31.0, end=40.0) == {"gross_motion"}
    assert max(r.motion for t, r in results if 31.0 <= t <= 40.0) > CFG.gross_motion_threshold
    # Calm again: periodic as soon as a clean stretch is long enough.
    assert statuses(results, start=40.0 + CFG.min_window_s + 2.0) == {"periodic"}
    # The child moved or breathed the whole time.
    assert "no_motion" not in statuses(results)
    assert "unusable" not in statuses(results, start=READY)


def test_a_single_twitch_does_not_turn_into_no_motion() -> None:
    chest = breathing(36.0)
    source = SyntheticSource(lambda t: chest(t) + (4.0 if 30.0 <= t < 30.4 else 0.0), duration_s=60.0)
    results = analyze(source)
    assert statuses(results, start=31.0, end=40.0) == {"gross_motion"}
    assert statuses(results, start=30.4 + 0.5 + CFG.min_window_s + 2.0) == {"periodic"}
    assert statuses(results, start=READY) == {"periodic", "gross_motion"}


def test_a_slow_turn_is_gross_motion_not_breathing() -> None:
    source = SyntheticSource(lambda t: 8.0 * min(1.0, max(0.0, (t - 30.0) / 4.0)), duration_s=60.0)
    results = analyze(source)
    assert statuses(results, start=32.0, end=40.0) == {"gross_motion"}
    assert "periodic" not in statuses(results)


def test_very_strong_breathing_is_never_called_no_motion() -> None:
    # A chest moving a whole pixel may exceed the gross threshold; either answer is fine.
    results = analyze(SyntheticSource(breathing(40.0, amplitude=1.0), duration_s=45.0))
    assert statuses(results, start=READY) <= {"periodic", "gross_motion"}


# --- unusable, never no_motion ------------------------------------------------


def test_no_frames_is_unusable() -> None:
    result = BreathingAnalyzer().evaluate(1_000.0)
    assert (result.status, result.rate, result.reason) == (Status.UNUSABLE, None, "no_frames")


@STILL_OR_BREATHING
def test_too_little_data_is_unusable(bpm: float) -> None:
    results = analyze(SyntheticSource(breathing(bpm), duration_s=CFG.min_window_s - 0.5))
    assert len(results) >= 11
    assert statuses(results) == {"unusable"}
    assert {r.reason for _, r in results} == {"insufficient_data"}


BAD_SCENES = {
    "dark": ("too_dark", partial(SyntheticSource, brightness=5.0, contrast=2.0)),
    "saturated": ("saturated", partial(SyntheticSource, brightness=252.0, contrast=30.0)),
    "covered_lens": ("low_contrast", partial(SyntheticSource, contrast=0.5)),
    "covered_lens_with_gain_noise": ("low_contrast", partial(SyntheticSource, contrast=0.5, noise_sigma=6.0)),
    "heavy_noise": ("too_noisy", partial(SyntheticSource, noise_sigma=30.0)),
}


@STILL_OR_BREATHING
@pytest.mark.parametrize("scene", BAD_SCENES)
def test_bad_pictures_are_unusable(scene: str, bpm: float) -> None:
    reason, make_source = BAD_SCENES[scene]
    results = analyze(make_source(breathing(bpm), duration_s=40.0))
    assert len(results) == 41
    assert statuses(results) == {"unusable"}
    assert {r.reason for _, r in results} == {reason}


def test_invalid_pixels_are_unusable_and_wrong_shapes_are_rejected() -> None:
    analyzer = BreathingAnalyzer()
    frame = SyntheticSource().render(0.0)
    frame[3, 3] = np.nan
    analyzer.add_frame(1.0, frame)
    assert analyzer.evaluate(1.0).reason == "invalid_frame"
    with pytest.raises(ValueError):
        analyzer.add_frame(2.0, np.zeros((4, 4, 3)))
    with pytest.raises(ValueError):
        analyzer.add_frame(2.0, np.zeros((0, 4)))


@STILL_OR_BREATHING
def test_a_stalled_stream_turns_unusable(bpm: float) -> None:
    source = SyntheticSource(breathing(bpm), duration_s=30.0)
    analyzer = BreathingAnalyzer()
    before = analyze(source, analyzer=analyzer)[-1][1]
    assert before.status is (Status.PERIODIC if bpm else Status.NO_MOTION)
    last = source.start_ts + 30.0
    assert analyzer.evaluate(last + 1.0).status is before.status  # one late frame is tolerated
    for delay in (CFG.stale_after_s + 0.1, 5.0, 30.0, 3600.0):
        result = analyzer.evaluate(last + delay)
        check_invariants(result)
        assert (result.status, result.reason) == (Status.UNUSABLE, "stale")


def test_after_a_gap_the_old_data_is_not_reused() -> None:
    # Still scene: no_motion before the gap must not carry over to after it.
    analyzer = BreathingAnalyzer()
    assert analyze(SyntheticSource(duration_s=30.0), analyzer=analyzer)[-1][1].status is Status.NO_MOTION
    resumed = SyntheticSource(duration_s=30.0, start_ts=1_700_000_040.0, seed=1)
    results = analyze(resumed, analyzer=analyzer)
    assert statuses(results, end=CFG.min_window_s - 1.0) == {"unusable"}
    assert statuses(results, start=READY) == {"no_motion"}


def _feed(analyzer: BreathingAnalyzer, source: SyntheticSource, times: list[float]) -> list[str]:
    """Feed frames at the given times (seconds); evaluate after each. Returns the statuses."""
    seen = []
    for t in times:
        analyzer.add_frame(source.start_ts + t, source.render(t))
        result = analyzer.evaluate(source.start_ts + t)
        check_invariants(result)
        seen.append(result.status.value)
    return seen


def _irregular_times(kind: str) -> list[float]:
    rng = np.random.default_rng(0)
    if kind == "two_fps":
        return [i * 0.5 for i in range(80)]
    if kind == "bursts":  # four frames in quick succession, then nothing for most of a second
        return [s + i * 0.02 for s in range(40) for i in range(4)]
    if kind == "heavy_loss":  # 8 fps camera, 60 % of the frames lost
        return [i * 0.125 for i in range(320) if rng.random() > 0.6]
    if kind == "long_gaps":  # a 1.5 s hole every 5 s
        return [i * 0.125 for i in range(320) if (i * 0.125) % 5.0 >= 1.5]
    raise AssertionError(kind)


@STILL_OR_BREATHING
@pytest.mark.parametrize("kind", ["two_fps", "bursts", "heavy_loss", "long_gaps"])
def test_irregular_timestamps_are_unusable(kind: str, bpm: float) -> None:
    source = SyntheticSource(breathing(bpm))
    seen = _feed(BreathingAnalyzer(), source, _irregular_times(kind))
    assert len(seen) >= 80
    assert set(seen) == {"unusable"}


def test_timestamps_that_jump_back_or_repeat_restart_the_analysis() -> None:
    source = SyntheticSource()
    analyzer = BreathingAnalyzer()
    times = [i * 0.125 for i in range(160)]
    assert _feed(analyzer, source, times)[-1] == "no_motion"
    assert _feed(analyzer, source, [10.0])[-1] == "unusable"  # clock jumped back
    assert _feed(analyzer, source, [10.125, 10.125])[-1] == "unusable"  # duplicate
    assert analyzer.evaluate(source.start_ts + 10.125).reason == "insufficient_data"


def test_mild_jitter_is_tolerated() -> None:
    rng = np.random.default_rng(3)
    source = SyntheticSource(breathing(40.0))
    times = [i * 0.125 + rng.uniform(-0.03, 0.03) for i in range(320)]
    analyzer = BreathingAnalyzer()
    assert set(_feed(analyzer, source, times)[int(READY * 8) :]) == {"periodic"}
    assert analyzer.evaluate(source.start_ts + times[-1]).rate == pytest.approx(40.0, abs=3.0)


@STILL_OR_BREATHING
def test_a_frozen_picture_is_unusable(bpm: float) -> None:
    source = SyntheticSource(breathing(bpm), duration_s=30.0)
    analyzer = BreathingAnalyzer()
    before = analyze(source, analyzer=analyzer)[-1][1].status
    frozen = source.render(30.0)
    seen = []
    for i in range(1, 30 * 8):
        ts = source.start_ts + 30.0 + i / 8.0
        analyzer.add_frame(ts, frozen)
        seen.append((i / 8.0, analyzer.evaluate(ts)))
    # Until the freeze is recognised the previous answer stands; then unusable.
    # (The first frozen frame still differs from the last live one.)
    recognised = CFG.frozen_after_s + 1.0 / 8.0
    assert {r.status for t, r in seen if t < recognised} == {before}
    assert {(r.status, r.reason) for t, r in seen if t >= recognised} == {(Status.UNUSABLE, "frozen")}
    if bpm:
        assert Status.NO_MOTION not in {r.status for _, r in seen}
    # Live again: the frozen stretch must not count as evidence of stillness.
    live = SyntheticSource(duration_s=10.0, start_ts=source.start_ts + 60.0, seed=5)
    assert statuses(analyze(live, analyzer=analyzer)) == {"unusable"}


def test_breathing_child_with_data_faults_is_never_no_motion() -> None:
    """Random dark, saturated, noisy, frozen and missing stretches while the child breathes."""
    kinds = ["dark", "saturated", "noisy", "frozen", "gap", "jitter"]
    total = {"periodic": 0, "unusable": 0}
    for seed in range(12):
        rng = np.random.default_rng(seed)
        bpm = float(rng.uniform(25.0, 70.0))
        source = SyntheticSource(breathing(bpm), seed=seed, noise_sigma=float(rng.uniform(1.0, 4.0)))
        faults = sorted(
            (float(rng.uniform(5.0, 110.0)), float(rng.uniform(0.3, 8.0)), str(rng.choice(kinds)))
            for _ in range(6)
        )
        analyzer = BreathingAnalyzer()
        held = None
        for i in range(120 * 8):
            t = i / 8.0
            active = {kind for start, length, kind in faults if start <= t < start + length}
            if "gap" in active:
                continue
            frame = source.render(t)
            if "dark" in active:
                frame = np.clip(frame * 0.04, 0.0, 255.0)
            if "saturated" in active:
                frame = np.clip(frame * 4.0, 0.0, 255.0)
            if "noisy" in active:
                frame = np.clip(frame + rng.normal(0.0, 35.0, frame.shape), 0.0, 255.0)
            if "frozen" in active:
                frame = held = frame if held is None else held
            else:
                held = None
            ts = source.start_ts + t + (float(rng.uniform(-0.04, 0.04)) if "jitter" in active else 0.0)
            analyzer.add_frame(ts, frame)
            result = analyzer.evaluate(ts)
            check_invariants(result)
            assert result.status is not Status.NO_MOTION, (seed, t, sorted(active), result)
            if result.status is Status.PERIODIC:
                assert result.rate == pytest.approx(bpm, abs=4.0)
            total[result.status.value] = total.get(result.status.value, 0) + 1
    # The scenario is not trivially unusable throughout, and the faults did bite.
    assert total["periodic"] > 2000 and total["unusable"] > 2000


def test_bad_frames_in_the_middle_restart_the_analysis() -> None:
    dark = (30.0, 33.0)
    source = SyntheticSource(
        breathing(40.0), duration_s=70.0, gain=lambda t: 0.04 if dark[0] <= t < dark[1] else 1.0
    )
    results = analyze(source)
    assert statuses(results, start=READY, end=29.0) == {"periodic"}
    assert {r.reason for t, r in results if dark[0] <= t < dark[1]} == {"too_dark"}
    assert statuses(results, start=dark[0], end=dark[1] + CFG.min_window_s - 1.0) == {"unusable"}
    assert statuses(results, start=dark[1] + READY) == {"periodic"}
    assert "no_motion" not in statuses(results)


# --- periodic, but not breathing ----------------------------------------------


@pytest.mark.parametrize(
    ("hz", "amplitude"), [(0.1, 0.3), (0.1, 1.0), (3.0, 0.1), (3.0, 0.3), (4.0, 0.3)]
)
def test_movement_outside_the_band_is_not_breathing(hz: float, amplitude: float) -> None:
    source = SyntheticSource(
        lambda t: amplitude * math.sin(2.0 * math.pi * hz * t), fps=10.0, duration_s=60.0
    )
    results = analyze(source)
    assert "periodic" not in statuses(results)
    assert max(r.confidence for _, r in results) < 0.5 * CFG.periodic_confidence


@pytest.mark.parametrize("hz", [0.1, 0.7, 1.0])
def test_lighting_flicker_is_not_breathing(hz: float) -> None:
    # 20 % brightness flicker of the whole ROI, also at breathing-like frequencies.
    source = SyntheticSource(
        gain=lambda t: 1.0 + 0.2 * math.sin(2.0 * math.pi * hz * t), fps=10.0, duration_s=60.0
    )
    results = analyze(source)
    assert statuses(results, start=READY) == {"no_motion"}
    assert max(r.confidence for _, r in results) < 0.5 * CFG.periodic_confidence


def test_breathing_is_still_found_under_lighting_flicker() -> None:
    source = SyntheticSource(
        breathing(40.0), gain=lambda t: 1.0 + 0.2 * math.sin(2.0 * math.pi * 0.1 * t), duration_s=50.0
    )
    for t, result in analyze(source):
        if t >= READY:
            assert result.status is Status.PERIODIC
            assert result.rate == pytest.approx(40.0, abs=3.0)


# --- precomputed motion signals -----------------------------------------------

T = np.arange(0.0, 25.0, 0.125)


@pytest.mark.parametrize("bpm", [20.0, 30.0, 45.0, 60.0, 85.0])
def test_precomputed_signal_in_band(bpm: float) -> None:
    signal = np.sin(2.0 * np.pi * bpm / 60.0 * T) + np.random.default_rng(0).normal(0.0, 0.3, T.size)
    found = estimate_periodicity(T, signal)
    assert found.rate == pytest.approx(bpm, abs=1.0)
    assert found.confidence > 0.8
    assert found.amplitude == pytest.approx(math.sqrt(0.5), rel=0.15)  # RMS of a unit sinusoid


@pytest.mark.parametrize("hz", [0.05, 0.1, 0.2, 1.7, 2.0, 3.0])
def test_precomputed_signal_out_of_band_has_no_confidence(hz: float) -> None:
    assert estimate_periodicity(T, np.sin(2.0 * np.pi * hz * T)).confidence == 0.0
    # With a breathing component added, that one is found instead.
    both = 5.0 * np.sin(2.0 * np.pi * hz * T) + np.sin(2.0 * np.pi * 0.7 * T)
    if hz < 0.15 or hz > 1.9:
        assert estimate_periodicity(T, both).rate == pytest.approx(42.0, abs=1.5)


def test_columns_moving_in_opposite_directions_do_not_cancel() -> None:
    wave = np.sin(2.0 * np.pi * 0.5 * T)
    found = estimate_periodicity(T, np.column_stack([wave, -wave]))
    assert found.rate == pytest.approx(30.0, abs=0.5)
    assert found.confidence > 0.95


def test_precomputed_signal_on_uneven_timestamps() -> None:
    t = np.sort(T + np.random.default_rng(1).uniform(-0.04, 0.04, T.size))
    assert estimate_periodicity(t, np.sin(2.0 * np.pi * 0.8 * t)).rate == pytest.approx(48.0, abs=1.0)


def test_unsuitable_precomputed_input_has_no_confidence() -> None:
    assert estimate_periodicity(T[:5], np.ones(5)).confidence == 0.0  # too short
    assert estimate_periodicity(T, np.full(T.size, 3.0)).confidence == 0.0  # constant
    assert estimate_periodicity(T[::-1], np.sin(T)).confidence == 0.0  # time runs backwards
    assert estimate_periodicity(T, np.full(T.size, np.nan)).confidence == 0.0
    assert estimate_periodicity(T[:16], np.sin(2 * np.pi * 0.5 * T[:16])).confidence == 0.0  # 2 s
