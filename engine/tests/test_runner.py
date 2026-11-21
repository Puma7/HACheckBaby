"""The loop end to end: synthetic frames in, MQTT messages out (fake client, fake clock)."""

from __future__ import annotations

import logging
import os
import signal
import threading
from collections.abc import Iterator

import pytest
from helpers import STATUSES, FakeMqttClient, breathing

from checkbaby_engine import __main__ as cli
from checkbaby_engine import publisher as publisher_module
from checkbaby_engine.capture import Frame, SyntheticSource
from checkbaby_engine.config import MqttConfig
from checkbaby_engine.publisher import Publisher
from checkbaby_engine.runner import Engine
from checkbaby_engine.signal import BreathingAnalyzer


class Clock:
    def __init__(self, now: float = 1_700_000_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


class ScriptedSource:
    """Plays a synthetic scene on a fake clock, then fails in a chosen way."""

    def __init__(self, scene: SyntheticSource, clock: Clock, then: str = "stall", step_s: float = 0.25) -> None:
        self.scene, self.clock, self.then, self.step_s = scene, clock, then, step_s
        self.closed = False
        self.reads = 0

    def read(self, timeout: float) -> Frame | None:
        self.reads += 1
        frame = self.scene.read()
        if frame is not None:
            self.clock.now = frame.ts
            return frame
        self.clock.now += self.step_s
        if self.then == "raise":
            raise RuntimeError("camera rtsp://user:hunter2@cam/stream is gone")
        return None

    def close(self) -> None:
        self.closed = True


def _engine(source: ScriptedSource, clock: Clock) -> tuple[Engine, FakeMqttClient]:
    client = FakeMqttClient()
    publisher = Publisher(MqttConfig(), "nursery", client)
    return Engine(source, BreathingAnalyzer(), publisher, clock=clock, sleep=lambda _s: None), client


def test_breathing_scene_ends_up_as_periodic_state_messages() -> None:
    clock = Clock()
    scene = SyntheticSource(breathing(40.0), duration_s=40.0, start_ts=clock.now)
    engine, client = _engine(ScriptedSource(scene, clock), clock)
    for _ in range(40 * 8 + 1):
        engine.step()
    states = [m.json for m in client.on("/state")]
    assert [s["status"] for s in states[:6]] == ["unusable"] * 6  # not enough data yet
    assert all(set(s) == {"status", "rate", "confidence", "motion", "ts"} for s in states)
    assert {s["status"] for s in states} == {"unusable", "periodic"}
    periodic = [s for s in states if s["status"] == "periodic"]
    assert len(periodic) >= 12
    assert all(s["rate"] == pytest.approx(40.0, abs=3.0) and s["confidence"] >= 0.3 for s in periodic)
    stamps = [s["ts"] for s in states]
    assert stamps[0] == pytest.approx(clock.now - 40.0)
    assert max(b - a for a, b in zip(stamps, stamps[1:], strict=False)) <= 2.0 + 1e-6
    # Periodic is reported as soon as 12 s of frames are there.
    assert periodic[0]["ts"] - stamps[0] == pytest.approx(12.0, abs=1.0)


@pytest.mark.parametrize("failure", ["stall", "raise"])
def test_a_failing_source_keeps_publishing_unusable(failure: str, caplog: pytest.LogCaptureFixture) -> None:
    clock = Clock()
    scene = SyntheticSource(breathing(40.0), duration_s=20.0, start_ts=clock.now)
    source = ScriptedSource(scene, clock, then=failure)
    engine, client = _engine(source, clock)
    with caplog.at_level(logging.DEBUG):
        for _ in range(20 * 8 + 1):
            engine.step()
        healthy = len(client.on("/state"))
        assert client.on("/state")[-1].json["status"] == "periodic"
        failed_at = clock.now
        for _ in range(240):  # one minute without frames
            engine.step()
    after = [m.json for m in client.on("/state")[healthy:]]
    # Never silent: a message at least every 2 s for the whole outage ...
    stamps = [failed_at] + [s["ts"] for s in after]
    assert max(b - a for a, b in zip(stamps, stamps[1:], strict=False)) <= 2.0 + 1e-6
    assert stamps[-1] >= failed_at + 59.0
    # ... and once the last frame is stale (2 s) the change to unusable goes out with
    # the next evaluation (1 s), not with the next 2 s tick; from then on nothing else.
    first_unusable = min(s["ts"] for s in after if s["status"] == "unusable")
    assert failed_at + 2.0 < first_unusable <= failed_at + 2.0 + 1.0 + source.step_s
    late = [s for s in after if s["ts"] >= first_unusable]
    assert len(late) >= 25
    assert {s["status"] for s in late} == {"unusable"}
    assert {s["status"] for s in after} <= {"periodic", "unusable"}  # never no_motion
    assert all(s["rate"] is None and s["confidence"] == 0.0 for s in late)
    assert "hunter2" not in caplog.text
    if failure == "raise":
        assert caplog.text.count("frame source failed") == 1  # logged once, not per retry


def test_a_source_that_never_delivers_is_unusable_from_the_start() -> None:
    clock = Clock()
    scene = SyntheticSource(duration_s=-1.0)  # no frames at all
    engine, client = _engine(ScriptedSource(scene, clock, then="raise", step_s=0.5), clock)
    for _ in range(40):
        engine.step()
    states = [m.json for m in client.on("/state")]
    assert len(states) >= 10
    assert {s["status"] for s in states} == {"unusable"}


def test_run_announces_online_and_always_ends_with_offline() -> None:
    clock = Clock()
    scene = SyntheticSource(duration_s=3.0, start_ts=clock.now)
    source = ScriptedSource(scene, clock)
    engine, client = _engine(source, clock)
    stop = threading.Event()
    original = source.read

    def read(timeout: float) -> Frame | None:
        if source.reads >= 40:
            stop.set()
        return original(timeout)

    source.read = read  # type: ignore[method-assign]
    engine.run(stop)
    availability = [(m.payload, m.retain) for m in client.on("/availability")]
    assert availability == [("online", True), ("offline", True)]
    assert client.messages[-1].payload == "offline"
    assert client.on("/state") and source.closed
    assert client.calls[-2:] == [("disconnect",), ("loop_stop",)]


def test_run_says_offline_even_when_the_loop_dies() -> None:
    clock = Clock()
    engine, client = _engine(ScriptedSource(SyntheticSource(duration_s=1.0), clock), clock)

    def boom() -> float:
        raise KeyboardInterrupt

    engine._clock = boom
    with pytest.raises(KeyboardInterrupt):
        engine.run(threading.Event())
    assert client.messages[-1].payload == "offline" and client.messages[-1].retain


@pytest.fixture
def restore_signal_handlers() -> Iterator[None]:
    saved = {s: signal.getsignal(s) for s in (signal.SIGTERM, signal.SIGINT)}
    yield
    for signum, handler in saved.items():
        signal.signal(signum, handler)


@pytest.mark.usefixtures("restore_signal_handlers")
def test_sigterm_sets_the_stop_event() -> None:
    stop = threading.Event()
    cli.install_signal_handlers(stop)
    assert not stop.is_set()
    signal.raise_signal(signal.SIGTERM)
    assert stop.is_set()


@pytest.mark.usefixtures("restore_signal_handlers")
def test_main_runs_until_sigterm_and_logs_no_credentials(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """The real entry point with the synthetic source in real time (about one second)."""
    client = FakeMqttClient()
    monkeypatch.setattr(publisher_module, "_paho_client", lambda client_id: client)
    for key in [k for k in os.environ if k.startswith("CHECKBABY_")]:
        monkeypatch.delenv(key)
    monkeypatch.setenv("CHECKBABY_RTSP_URL", "synthetic://40")
    monkeypatch.setenv("CHECKBABY_ENGINE_ID", "bed_1")
    monkeypatch.setenv("CHECKBABY_MQTT_USERNAME", "engine")
    monkeypatch.setenv("CHECKBABY_MQTT_PASSWORD", "mqtt-s3cr3t")
    timer = threading.Timer(1.0, os.kill, (os.getpid(), signal.SIGTERM))
    timer.start()
    try:
        with caplog.at_level(logging.DEBUG):
            assert cli.main([]) == 0
    finally:
        timer.cancel()
    assert ("username_pw_set", "engine", "mqtt-s3cr3t") in client.calls
    assert [m.payload for m in client.on("bed_1/availability")] == ["online", "offline"]
    states = [m.json for m in client.on("bed_1/state")]
    assert states and {s["status"] for s in states} <= STATUSES
    assert states[0]["status"] == "unusable"  # one second of data is not enough to say anything
    assert "mqtt-s3cr3t" not in caplog.text
    assert "not a medical monitor" in caplog.text


def test_main_reports_a_bad_configuration_without_starting(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    for key in [k for k in os.environ if k.startswith("CHECKBABY_")]:
        monkeypatch.delenv(key)
    assert cli.main([]) == 2
    assert "rtsp_url is required" in capsys.readouterr().err
    monkeypatch.setenv("CHECKBABY_RTSP_URL", "synthetic://fast")
    assert cli.main([]) == 2
    assert "synthetic://" in capsys.readouterr().err
