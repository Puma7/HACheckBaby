"""MQTT contract, against a fake client. No broker."""

from __future__ import annotations

import inspect
import json
import math

import pytest
from helpers import FakeMqttClient

from checkbaby_engine.config import MqttConfig
from checkbaby_engine.publisher import Publisher, _paho_client, state_payload
from checkbaby_engine.signal import Result, Status

PERIODIC = Result(Status.PERIODIC, 41.26, 0.8765, 0.4321, "periodic")
STILL = Result(Status.NO_MOTION, None, 0.05, 0.1, "no_motion")
MOVING = Result(Status.GROSS_MOTION, None, 0.0, 12.5, "gross_motion")
UNUSABLE = Result(Status.UNUSABLE, None, 0.0, 0.0, "stale")


def _publisher(**mqtt: object) -> tuple[Publisher, FakeMqttClient]:
    client = FakeMqttClient()
    return Publisher(MqttConfig(**mqtt), "nursery", client), client  # type: ignore[arg-type]


def test_availability_online_retained_with_offline_as_last_will() -> None:
    publisher, client = _publisher(host="broker.lan", port=1884)
    publisher.start()
    topic = "checkbaby/engine/nursery/availability"
    assert client.will is not None
    assert (client.will.topic, client.will.payload, client.will.retain) == (topic, "offline", True)
    assert ("connect_async", "broker.lan", 1884, 30) in client.calls
    # The will must be registered before the connection is started.
    assert client.calls.index(("connect_async", "broker.lan", 1884, 30)) < client.calls.index(("loop_start",))
    assert [(m.topic, m.payload, m.retain) for m in client.messages] == [(topic, "online", True)]


def test_online_is_published_again_after_every_reconnect_but_not_on_refusal() -> None:
    publisher, client = _publisher()
    publisher.start()
    client.on_connect(client, None, None, 0, None)
    assert [m.payload for m in client.on("/availability")] == ["online", "online"]

    class Refused:
        is_failure = True

    client.on_connect(client, None, None, Refused(), None)
    assert len(client.on("/availability")) == 2


def test_credentials_are_passed_to_the_client_only_when_set() -> None:
    publisher, client = _publisher(username="engine", password="pw")
    publisher.start()
    assert ("username_pw_set", "engine", "pw") in client.calls
    publisher, client = _publisher()
    publisher.start()
    assert not [c for c in client.calls if c[0] == "username_pw_set"]


@pytest.mark.parametrize("result", [PERIODIC, STILL, MOVING, UNUSABLE])
def test_state_payload_shape(result: Result) -> None:
    publisher, client = _publisher()
    assert publisher.update(result, 1_700_000_000.1234)
    (message,) = client.messages
    assert (message.topic, message.retain) == ("checkbaby/engine/nursery/state", False)
    data = message.json
    assert list(data) == ["status", "rate", "confidence", "motion", "ts"]
    assert data["status"] == result.status.value
    assert isinstance(data["confidence"], float) and 0.0 <= data["confidence"] <= 1.0
    assert isinstance(data["motion"], float) and data["motion"] == pytest.approx(result.motion, abs=1e-3)
    assert isinstance(data["ts"], float) and data["ts"] == pytest.approx(1_700_000_000.123)
    if result.status is Status.PERIODIC:
        assert data["rate"] == pytest.approx(41.3)
    else:
        assert data["rate"] is None


def test_rate_is_null_unless_periodic_even_if_a_rate_is_passed() -> None:
    odd = Result(Status.GROSS_MOTION, 55.0, 0.2, 9.0, "x")
    assert json.loads(state_payload(odd, 1.0))["rate"] is None


def test_payload_is_always_valid_json_numbers() -> None:
    broken = Result(Status.PERIODIC, math.nan, math.inf, -math.inf, "x")
    assert json.loads(state_payload(broken, 2.0)) == {
        "status": "periodic", "rate": None, "confidence": 0.0, "motion": 0.0, "ts": 2.0,
    }
    assert json.loads(state_payload(Result(Status.NO_MOTION, None, 1.7, -3.0, "x"), 2.0))["confidence"] == 1.0


def test_state_is_published_every_two_seconds_and_at_once_on_a_status_change() -> None:
    publisher, client = _publisher()
    sent = [publisher.update(STILL, t) for t in (0.0, 1.0, 1.9, 2.0, 3.0, 4.0, 4.5)]
    assert sent == [True, False, False, True, False, True, False]
    # Status changes do not wait for the interval, in either direction.
    assert publisher.update(PERIODIC, 4.6)
    assert publisher.update(UNUSABLE, 4.7)
    assert publisher.update(UNUSABLE, 5.0) is False
    assert publisher.update(STILL, 5.1)
    assert publisher.update(STILL, 7.0) is False  # the interval restarts at the change
    assert publisher.update(STILL, 7.1)
    states = [(m.json["status"], m.json["ts"]) for m in client.on("/state")]
    assert states == [
        ("no_motion", 0.0), ("no_motion", 2.0), ("no_motion", 4.0), ("periodic", 4.6),
        ("unusable", 4.7), ("no_motion", 5.1), ("no_motion", 7.1),
    ]


def test_topic_prefix_and_interval_are_configurable() -> None:
    client = FakeMqttClient()
    publisher = Publisher(MqttConfig(topic_prefix="home/cb", publish_interval_s=5.0), "bed-2", client)
    publisher.start()
    assert [publisher.update(STILL, t) for t in (0.0, 2.0, 4.9, 5.0)] == [True, False, False, True]
    assert {m.topic for m in client.messages} == {"home/cb/bed-2/availability", "home/cb/bed-2/state"}
    assert client.will is not None and client.will.topic == "home/cb/bed-2/availability"


def test_stop_publishes_offline_retained_then_disconnects() -> None:
    publisher, client = _publisher()
    publisher.start()
    publisher.update(STILL, 0.0)
    publisher.stop()
    last = client.messages[-1]
    assert (last.topic, last.payload, last.retain) == ("checkbaby/engine/nursery/availability", "offline", True)
    # It waits for the offline message to leave before it hangs up.
    assert client.calls[-3:] == [("wait_for_publish", 2.0), ("disconnect",), ("loop_stop",)]


def test_the_fake_matches_the_real_paho_client() -> None:
    """Every call the publisher makes must be valid for paho-mqtt's v2 client."""
    real = _paho_client("checkbaby-test")  # constructing a client opens no connection
    assert type(real).__module__ == "paho.mqtt.client"
    calls = {
        "username_pw_set": (("user", "pw"), {}),
        "will_set": (("t", "offline"), {"qos": 1, "retain": True}),
        "connect_async": (("host", 1883), {"keepalive": 30}),
        "publish": (("t", "payload"), {"qos": 0, "retain": False}),
        "loop_start": ((), {}),
        "loop_stop": ((), {}),
        "disconnect": ((), {}),
    }
    for name, (args, kwargs) in calls.items():
        inspect.signature(getattr(real, name)).bind(*args, **kwargs)
        assert hasattr(FakeMqttClient, name)
    info = real.publish("t", "payload", qos=1, retain=True)
    inspect.signature(info.wait_for_publish).bind(timeout=2.0)
    real.on_connect = Publisher(MqttConfig(), "x", real)._on_connect
    # The v2 callback gets (client, userdata, flags, reason_code, properties).
    assert len(inspect.signature(real.on_connect).parameters) == 5
    # Publishing while disconnected must not raise (paho reports it via the return code).
    Publisher(MqttConfig(), "x", real).update(STILL, 0.0)
    Publisher(MqttConfig(), "x", real).stop()
