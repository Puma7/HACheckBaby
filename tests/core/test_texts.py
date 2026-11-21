"""Texts, push payloads and reports."""

from __future__ import annotations

import pytest

from custom_components.checkbaby.push import build_clear, build_push, notification_tag
from custom_components.checkbaby.report import night_report, night_report_text, quick_check_text
from custom_components.checkbaby.sleep_log import SleepLog
from custom_components.checkbaby.texts import _DE, _EN, alert_message, alert_title, problem_names, state_name, text
from custom_components.checkbaby.types import AlertKind, AlertLevel, ChildState

from .helpers import Night


def test_both_languages_have_the_same_texts_and_placeholders() -> None:
    assert set(_DE) == set(_EN)
    for key, english in _EN.items():
        placeholders = {part.split("}")[0] for part in english.split("{")[1:]}
        german = {part.split("}")[0] for part in _DE[key].split("{")[1:]}
        assert german == placeholders, key


@pytest.mark.parametrize("language", ["en", "de", "de-CH", "fr"])
@pytest.mark.parametrize("kind", list(AlertKind))
@pytest.mark.parametrize("level", [AlertLevel.WARNING, AlertLevel.CRITICAL])
def test_every_alert_has_a_message(language: str, kind: AlertKind, level: AlertLevel) -> None:
    detail = {"seconds": 95, "problems": ["frigate", "custom"], "hazards": ["toy"], "reason": "r", "temperature": 25.5}
    message = alert_message(language, "Mia", kind, level, detail)
    assert message
    assert "{" not in message
    assert alert_title(language, "Mia", level).endswith("Mia")


def test_messages_carry_their_details() -> None:
    assert alert_message("en", "Mia", AlertKind.CRYING, AlertLevel.WARNING, {"seconds": 20}) == "Mia is crying (20 s)."
    assert "mehreren Minuten" in alert_message("de", "Mia", AlertKind.CRYING, AlertLevel.CRITICAL, {})
    failure = alert_message("de", "Mia", AlertKind.MONITORING_FAILURE, AlertLevel.WARNING, {"problems": ["frigate", "x"]})
    assert "Frigate offline, x" in failure
    assert "4 min" in alert_message("en", "Mia", AlertKind.INTERRUPTION, AlertLevel.WARNING, {"seconds": 240})
    assert problem_names("en", ["mqtt"]) == "MQTT disconnected"
    assert state_name("de", ChildState.ASLEEP) == "schläft"
    assert text("xx", "action_ack") == "Seen"


def test_critical_push_breaks_through_silent_mode_on_both_platforms() -> None:
    payload = build_push(
        language="en", child="Mia", entry_id="abc", kind=AlertKind.NO_BREATHING, level=AlertLevel.CRITICAL,
        detail={}, camera_entity="camera.nursery", dashboard_path="/lovelace/baby",
    )  # fmt: skip
    data = payload["data"]
    assert payload["title"] == "ALARM · Mia"
    assert data["push"]["sound"] == {"name": "default", "critical": 1, "volume": 1.0}
    assert (data["channel"], data["ttl"], data["priority"]) == ("alarm_stream", 0, "high")
    assert data["tag"] == notification_tag("abc", AlertKind.NO_BREATHING) == "checkbaby_abc_no_breathing"
    assert data["image"] == "/api/camera_proxy/camera.nursery"
    assert data["entity_id"] == "camera.nursery"
    assert [action["action"] for action in data["actions"]] == ["CHECKBABY_ACK_abc", "CHECKBABY_SNOOZE_abc", "URI"]
    assert data["actions"][2]["uri"] == "/lovelace/baby"


def test_warning_push_is_time_sensitive_and_works_without_a_camera() -> None:
    payload = build_push(
        language="de", child="Mia", entry_id="abc", kind=AlertKind.CRYING, level=AlertLevel.WARNING,
        detail={"seconds": 15}, camera_entity=None, dashboard_path="/lovelace",
    )  # fmt: skip
    data = payload["data"]
    assert payload["message"] == "Mia weint (15 s)."
    assert data["push"] == {"interruption-level": "time-sensitive"}
    assert data["channel"] == "CheckBaby"
    assert "image" not in data
    assert build_clear("abc", AlertKind.CRYING) == {
        "message": "clear_notification",
        "data": {"tag": "checkbaby_abc_crying"},
    }


def test_night_report_numbers_and_text() -> None:
    log = SleepLog()
    log.on_state(ChildState.AWAKE, ChildState.ASLEEP, 1000.0, mode="night", place=None)
    log.on_state(ChildState.ASLEEP, ChildState.CRYING, 1000.0 + 7200, mode="night", place=None)
    log.on_state(ChildState.CRYING, ChildState.AWAKE, 1000.0 + 7500, mode="night", place=None)
    log.on_state(ChildState.AWAKE, ChildState.ASLEEP, 1000.0 + 9000, mode="night", place=None)

    report = night_report(log, 0.0, 1000.0 + 12600)

    assert report["slept_seconds"] == 7200 + 3600
    assert report["cried_seconds"] == 300
    assert report["wakeups"] == 1
    assert report["sleep_phases"] == 2
    assert report["longest_stretch_seconds"] == 7200
    assert night_report_text("en", "Mia", report) == (
        "Mia: slept 3 h 0 min since the evening, woke 1 time(s), cried 5 min, longest stretch 120 min."
    )
    assert "kein Schlaf" in night_report_text("de", "Mia", night_report(SleepLog(), 0.0, 100.0))
    # Sleep before the window does not count.
    assert night_report(log, 1000.0 + 12000, 1000.0 + 12600)["slept_seconds"] == 600


def test_quick_check_text_mentions_what_matters() -> None:
    night = Night()
    night.advance(300)
    calm = night.monitor.snapshot(night.now, night.now - 400, night.now - 400)
    assert quick_check_text("en", "Mia", calm, night.now) == "Mia: asleep. Asleep for 5 min."

    night.cry()
    night.audio_alive = False
    night.advance(70)
    busy = night.monitor.snapshot(night.now, night.now - 400, night.now - 400)
    summary = quick_check_text("de", "Mia", busy, night.now)
    assert "unbekannt" in summary
    assert "Aktiver Alarm" in summary
    assert "Störungen: kein Ton von der Kamera" in summary
