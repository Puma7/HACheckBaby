"""Frame sources. The RTSP reader runs against a fake container; one test decodes a
real (synthetic) video file with PyAV. No camera, no network."""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from checkbaby_engine.capture import Frame, RtspSource, SyntheticSource, crop_and_downsize
from checkbaby_engine.config import Roi

URL = "rtsp://viewer:s3cr3t-pw@camera.local:554/sub"


# --- crop_and_downsize --------------------------------------------------------


def test_crop_takes_the_roi_and_averages_whole_pixels() -> None:
    gray = np.zeros((120, 160), dtype=np.uint8)
    gray[30:90, 80:160] = 200  # the ROI: right half, middle rows
    gray[30:90:2, 80:160:2] = 100  # fine detail that averaging must blend, not drop
    image = crop_and_downsize(gray, Roi(x=0.5, y=0.25, w=0.5, h=0.5), width=40)
    assert image.dtype == np.float32
    assert image.shape == (30, 40)  # 80 x 60 pixels shrunk by 2
    assert np.allclose(image, 175.0)  # mean of 100, 200, 200, 200
    assert crop_and_downsize(gray, Roi(0.0, 0.0, 0.5, 0.25), width=40).max() == 0.0


def test_crop_never_enlarges_and_never_returns_nothing() -> None:
    gray = np.arange(48 * 64, dtype=np.uint8).reshape(48, 64)
    assert np.array_equal(crop_and_downsize(gray, Roi(), width=64), gray)
    assert crop_and_downsize(gray, Roi(), width=320).shape == (48, 64)
    assert crop_and_downsize(gray, Roi(), width=16).shape == (12, 16)
    assert crop_and_downsize(gray, Roi(0.99, 0.99, 0.01, 0.01), width=64).shape == (1, 1)
    assert crop_and_downsize(gray, Roi(0.0, 0.0, 1.0, 0.02), width=16).shape[0] >= 1


# --- synthetic source ---------------------------------------------------------


def test_synthetic_source_is_deterministic_and_paced_by_fps() -> None:
    def frames() -> list[Frame]:
        source = SyntheticSource(fps=5.0, duration_s=2.0, seed=7)
        out = []
        while (frame := source.read()) is not None:
            out.append(frame)
        return out

    first, second = frames(), frames()
    assert len(first) == 11
    assert np.allclose(np.diff([f.ts for f in first]), 0.2)
    assert all(np.array_equal(a.image, b.image) for a, b in zip(first, second, strict=True))
    assert first[0].image.shape == (48, 64) and first[0].image.dtype == np.float32
    assert first[0].image.mean() == pytest.approx(110.0, abs=15.0)
    assert not np.array_equal(first[0].image, first[1].image)  # sensor noise differs per frame


def test_synthetic_displacement_shifts_the_picture() -> None:
    still = SyntheticSource(noise_sigma=0.0)
    moved = SyntheticSource(displacement=lambda t: 3.0, noise_sigma=0.0)
    assert np.array_equal(moved.render(0.0)[3:], still.render(0.0)[:-3])


# --- RTSP reader against a fake container -------------------------------------


class FakeAvFrame:
    def __init__(self, time: float | None, value: int = 120) -> None:
        self.time = time
        self.value = value
        self.formats: list[str] = []

    def to_ndarray(self, format: str) -> np.ndarray[Any, Any]:
        self.formats.append(format)
        picture = np.full((90, 160), 30, dtype=np.uint8)
        picture[:, 80:] = self.value  # right half carries the value
        return picture


class FakeContainer:
    def __init__(self, frames: list[FakeAvFrame], clock: list[float], error: Exception | None = None) -> None:
        self.frames = frames
        self.clock = clock
        self.error = error
        self.closed = False

    def decode(self, video: int) -> Any:
        assert video == 0
        start = self.clock[0]
        for frame in self.frames:
            if frame.time is not None:
                self.clock[0] = start + frame.time  # the wall clock runs with the stream
            yield frame
        if self.error is not None:
            raise self.error

    def close(self) -> None:
        self.closed = True


def _drain(source: RtspSource, count: int) -> list[Frame]:
    frames: list[Frame] = []
    deadline = time.monotonic() + 5.0
    while len(frames) < count and time.monotonic() < deadline:
        if (frame := source.read(timeout=0.2)) is not None:
            frames.append(frame)
    return frames


def test_rtsp_source_drops_to_target_fps_converts_and_crops() -> None:
    clock = [1_000.0]
    av_frames = [FakeAvFrame(i / 25.0) for i in range(100)]  # 4 s of a 25 fps camera
    container = FakeContainer(av_frames, clock)
    opened: list[str] = []
    done = threading.Event()

    def opener(url: str) -> FakeContainer:
        opened.append(url)
        if len(opened) > 1:
            done.wait(5.0)  # hold the reconnect so the test sees exactly one pass
            raise ConnectionError("gone")
        return container

    source = RtspSource(
        URL, Roi(0.5, 0.0, 0.5, 1.0), fps=8.0, frame_width=20,
        opener=opener, clock=lambda: clock[0], backoff_s=(0.01, 0.02),
    )
    try:
        frames = _drain(source, 34)
        assert source.read(timeout=0.1) is None  # nothing more to come
    finally:
        done.set()
        source.close()
    assert opened[0] == URL  # the real URL goes to the opener, the masked one only to the log
    # Every third frame of 25 fps: 8.3 fps, evenly spaced.
    assert len(frames) == 34
    assert np.allclose(np.diff([f.ts for f in frames]), 0.12, atol=1e-6)
    assert frames[0].ts == pytest.approx(1_000.0)
    converted = [f for f in av_frames if f.formats]
    assert len(converted) == 34 and all(f.formats == ["gray"] for f in converted)
    assert frames[0].image.shape == (22, 20)  # right half (80 x 90) shrunk by 4
    assert np.allclose(frames[0].image, 120.0)  # ROI is the right half only
    assert container.closed


def test_rtsp_source_reconnects_with_backoff_and_masks_the_url(caplog: pytest.LogCaptureFixture) -> None:
    clock = [5_000.0]
    attempts: list[float] = []
    stop = threading.Event()

    def opener(url: str) -> FakeContainer:
        attempts.append(time.monotonic())
        if len(attempts) == 1:
            raise OSError(f"Connection refused: '{url}'")  # FFmpeg-style text with the full URL
        if len(attempts) <= 3:
            raise OSError("401 Unauthorized (viewer / s3cr3t-pw)")  # the password on its own
        if len(attempts) == 4:
            # A stream that delivers and then breaks.
            return FakeContainer([FakeAvFrame(i / 8.0) for i in range(4)], clock, OSError("timeout"))
        stop.wait(5.0)
        raise OSError("still down")

    source = RtspSource(URL, Roi(), 8.0, 64, opener=opener, clock=lambda: clock[0], backoff_s=(0.05, 0.2))
    with caplog.at_level(logging.DEBUG, logger="checkbaby_engine"):
        try:
            assert source.read(timeout=0.01) is None  # down: read returns instead of blocking
            frames = _drain(source, 4)
        finally:
            stop.set()
            source.close()
    assert len(frames) == 4
    waits = np.diff(attempts[:4])
    assert waits[0] >= 0.05 and waits[1] >= 0.1 and waits[2] >= 0.2  # doubled, then capped
    assert waits[2] < 0.5
    text = caplog.text
    assert "stream error" in text and "stream open" in text
    assert "s3cr3t-pw" not in text
    assert "401 Unauthorized (viewer / ***)" in text
    assert "rtsp://viewer:***@camera.local:554/sub" in text


def test_rtsp_source_close_stops_the_reader_thread() -> None:
    def opener(url: str) -> FakeContainer:
        raise OSError("down")

    source = RtspSource(URL, Roi(), 8.0, 64, opener=opener, backoff_s=(30.0, 30.0))
    assert source.read(timeout=0.05) is None
    thread = source._thread
    assert thread is not None and thread.is_alive()
    source.close()  # must not wait out the 30 s backoff
    assert not thread.is_alive()


def test_rtsp_source_without_presentation_times_uses_the_clock() -> None:
    clock = [100.0]
    container = FakeContainer([FakeAvFrame(None)], clock)
    hold = threading.Event()

    def opener(url: str) -> FakeContainer:
        if container.closed:
            hold.wait(5.0)
            raise OSError("down")
        return container

    source = RtspSource(URL, Roi(), 8.0, 64, opener=opener, clock=lambda: clock[0])
    try:
        frames = _drain(source, 1)
    finally:
        hold.set()
        source.close()
    assert [f.ts for f in frames] == [100.0]


def test_rtsp_source_collapses_the_buffered_burst_after_connecting() -> None:
    """FFmpeg hands over a few seconds of buffered frames at once; they must not be
    stamped as if they had just been taken one after the other."""
    clock = [2_000.0]
    hold = threading.Event()

    class Burst(FakeContainer):
        def decode(self, video: int) -> Any:
            for frame in self.frames:
                assert frame.time is not None
                self.clock[0] = 2_000.0 + max(0.0, frame.time - 3.0)  # first 3 s arrive at once
                yield frame

    container = Burst([FakeAvFrame(i / 8.0) for i in range(8 * 8)], clock)

    def opener(url: str) -> FakeContainer:
        if container.closed:
            hold.wait(5.0)
            raise OSError("down")
        return container

    source = RtspSource(URL, Roi(), 8.0, 64, opener=opener, clock=lambda: clock[0])
    try:
        frames = _drain(source, 40)
        assert source.read(timeout=0.1) is None
    finally:
        hold.set()
        source.close()
    stamps = [f.ts for f in frames]
    assert len(frames) == 40  # one frame for the 3 s burst, then 39 live frames at 8 fps
    assert np.allclose(np.diff(stamps), 0.125, atol=1e-6)
    assert stamps[0] == pytest.approx(2_000.0) and stamps[-1] == pytest.approx(2_004.875)


# --- real PyAV decode of a generated file -------------------------------------


def test_rtsp_source_decodes_a_real_video_with_pyav(tmp_path: Path) -> None:
    av = pytest.importorskip("av")
    path = tmp_path / "pattern.mp4"
    with av.open(str(path), mode="w") as container:
        stream = container.add_stream("mpeg4", rate=10)
        stream.width, stream.height, stream.pix_fmt = 160, 96, "yuv420p"
        for _ in range(30):
            rgb = np.full((96, 160, 3), 40, dtype=np.uint8)
            rgb[:, 80:] = 200  # right half bright
            for packet in stream.encode(av.VideoFrame.from_ndarray(rgb, format="rgb24")):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)

    def read_roi(roi: Roi) -> list[Frame]:
        source = RtspSource(str(path), roi, fps=10.0, frame_width=20, backoff_s=(30.0, 30.0))
        try:
            # A file is read faster than real time, which looks like one long
            # buffered burst: exactly one frame comes out of it.
            return _drain(source, 1)
        finally:
            source.close()

    bright, dark = read_roi(Roi(0.5, 0.0, 0.5, 1.0)), read_roi(Roi(0.0, 0.0, 0.5, 1.0))
    assert len(bright) == 1 and len(dark) == 1
    assert bright[0].image.shape == (24, 20) and bright[0].image.dtype == np.float32
    # Full-range 200 becomes roughly 187 in video-range luma; the point is bright versus dark.
    assert 150.0 < float(bright[0].image[:, 4:].mean()) < 215.0
    assert 25.0 < float(dark[0].image[:, :-4].mean()) < 70.0
