"""Shared test helpers: synthetic scenes, a fake MQTT client. No network, no camera."""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from checkbaby_engine.capture import SyntheticSource
from checkbaby_engine.signal import BreathingAnalyzer, Result, SignalConfig, Status

STATUSES = {"periodic", "gross_motion", "no_motion", "unusable"}


def breathing(bpm: float, amplitude: float = 0.3) -> Callable[[float], float]:
    """Vertical shift in pixels of a chest moving at ``bpm`` breaths per minute."""
    return lambda t: amplitude * math.sin(2.0 * math.pi * bpm / 60.0 * t)


def check_invariants(result: Result) -> None:
    assert result.status.value in STATUSES
    assert (result.rate is not None) == (result.status is Status.PERIODIC)
    assert 0.0 <= result.confidence <= 1.0
    assert result.motion >= 0.0 and math.isfinite(result.motion)
    if result.rate is not None:
        assert 18.0 <= result.rate <= 90.0


def analyze(
    source: SyntheticSource,
    config: SignalConfig | None = None,
    analyzer: BreathingAnalyzer | None = None,
) -> list[tuple[float, Result]]:
    """Feed all frames; evaluate once per second. Returns (seconds since start, result)."""
    analyzer = analyzer or BreathingAnalyzer(config)
    results: list[tuple[float, Result]] = []
    due = source.start_ts
    while (frame := source.read()) is not None:
        analyzer.add_frame(frame.ts, frame.image)
        if frame.ts >= due:
            result = analyzer.evaluate(frame.ts)
            check_invariants(result)
            results.append((frame.ts - source.start_ts, result))
            due += 1.0
    return results


def statuses(results: list[tuple[float, Result]], start: float = 0.0, end: float = math.inf) -> set[str]:
    return {r.status.value for t, r in results if start <= t <= end}


@dataclass
class Message:
    topic: str
    payload: str
    qos: int
    retain: bool

    @property
    def json(self) -> dict[str, Any]:
        data = json.loads(self.payload)
        assert isinstance(data, dict)
        return data


@dataclass
class FakeMqttClient:
    """Records what the publisher does; ``loop_start`` simulates a successful connect."""

    connect_on_start: bool = True
    messages: list[Message] = field(default_factory=list)
    calls: list[tuple[Any, ...]] = field(default_factory=list)
    will: Message | None = None
    on_connect: Any = None

    def username_pw_set(self, username: str | None, password: str | None = None) -> None:
        self.calls.append(("username_pw_set", username, password))

    def will_set(self, topic: str, payload: str, qos: int, retain: bool) -> None:
        self.will = Message(topic, payload, qos, retain)

    def connect_async(self, host: str, port: int, keepalive: int) -> None:
        self.calls.append(("connect_async", host, port, keepalive))

    def loop_start(self) -> None:
        self.calls.append(("loop_start",))
        if self.connect_on_start:
            self.on_connect(self, None, None, 0, None)

    def loop_stop(self) -> None:
        self.calls.append(("loop_stop",))

    def publish(self, topic: str, payload: str, qos: int, retain: bool) -> FakeMqttClient:
        self.messages.append(Message(topic, payload, qos, retain))
        return self  # stands in for paho's MQTTMessageInfo

    def wait_for_publish(self, timeout: float | None = None) -> None:
        self.calls.append(("wait_for_publish", timeout))

    def disconnect(self) -> None:
        self.calls.append(("disconnect",))

    def on(self, topic_suffix: str) -> list[Message]:
        return [m for m in self.messages if m.topic.endswith(topic_suffix)]
