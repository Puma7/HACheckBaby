"""End to end: sources in, notifications out, through Home Assistant."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_mqtt_message,
    async_mock_service,
)
from pytest_homeassistant_custom_component.typing import MqttMockHAClient

from custom_components.checkbaby.coordinator import CheckBabyCoordinator
from custom_components.checkbaby.const import (
    CONF_AUDIO_URL,
    CONF_BED_ZONE,
    CONF_BREATH_RATE_ENTITY,
    CONF_CAMERA_ENTITY,
    CONF_CRY_ENTITY,
    CONF_DOOR_ENTITY,
    CONF_ENGINE_ID,
    CONF_FRIGATE_CAMERA,
    CONF_HEART_RATE_ENTITY,
    CONF_HEARTBEAT_BUTTONS,
    CONF_HUMIDITY_ENTITY,
    CONF_INTERNET_ENTITY,
    CONF_LEVEL_ENTITY,
    CONF_LOCAL_ALARM,
    CONF_MOTION_ENTITY,
    CONF_NOTIFY_SERVICES,
    CONF_PERSON_IS_CAREGIVER,
    CONF_PRESENCE_ENTITY,
    CONF_SMOKE_ENTITIES,
    CONF_TEMPERATURE_ENTITY,
    CONF_VOX_PLAYER,
    DOMAIN,
)

from .conftest import CAMERA, PARENT_A, PARENT_B, SIREN, advance, entity_id, make_entry, setup, state_of, turn_on

BASE = f"frigate/{CAMERA}"
Pushes = dict[str, list[ServiceCall]]


async def _start(
    hass: HomeAssistant, entry: MockConfigEntry, freezer: FrozenDateTimeFactory, *, armed: bool = True
) -> None:
    """Set up with Frigate online and sound coming in."""
    await setup(hass, entry)
    async_fire_mqtt_message(hass, "frigate/available", "online")
    await _sound(hass, freezer, 2)
    if armed:
        await turn_on(hass, entry, "monitoring")


async def _sound(hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: float, level: float = -50.0) -> None:
    """Let time pass while the camera keeps reporting a slightly varying level."""
    elapsed = 0.0
    while elapsed < seconds:
        async_fire_mqtt_message(hass, f"{BASE}/audio/dBFS", str(level + (0.3 if int(elapsed) % 4 else -0.3)))
        await advance(hass, freezer, 2)
        elapsed += 2


def _real(calls: list[ServiceCall]) -> list[dict[str, Any]]:
    """Pushes that show on the phone, without the clear messages."""
    return [dict(call.data) for call in calls if call.data.get("message") != "clear_notification"]


async def test_crying_from_warning_to_acknowledgement(
    hass: HomeAssistant,
    mqtt_mock: MqttMockHAClient,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    pushes: Pushes,
    local_alarm: Pushes,
) -> None:
    await _start(hass, config_entry, freezer)
    assert state_of(hass, config_entry, "sensor", "state") == "asleep"

    async_fire_mqtt_message(hass, f"{BASE}/audio/crying", "ON")
    await _sound(hass, freezer, 16)

    assert state_of(hass, config_entry, "sensor", "state") == "crying"
    assert state_of(hass, config_entry, "binary_sensor", "crying") == "on"
    assert state_of(hass, config_entry, "sensor", "alert_level") == "warning"
    assert state_of(hass, config_entry, "sensor", "alert_reason") == "crying"
    assert state_of(hass, config_entry, "binary_sensor", "alert_active") == "on"
    first = _real(pushes[PARENT_A])
    assert len(first) == 1
    assert first[0]["data"]["push"] == {"interruption-level": "time-sensitive"}
    assert first[0]["data"]["image"] == "/api/camera_proxy/camera.nursery"
    assert len(_real(pushes[PARENT_B])) == 1  # everyone is on duty by default
    event = hass.states.get(entity_id(hass, config_entry, "event", "alert"))
    assert event is not None
    assert (event.attributes["event_type"], event.attributes["level"]) == ("crying", "warning")

    # Nobody reacts: the local alarm joins after a minute, critical after three.
    await _sound(hass, freezer, 60)
    assert [call.data["entity_id"] for call in local_alarm["on"]] == [[SIREN]]
    await _sound(hass, freezer, 122)
    assert state_of(hass, config_entry, "sensor", "alert_level") == "critical"
    critical = _real(pushes[PARENT_B])[-1]
    assert critical["title"].startswith("ALARM")
    assert critical["data"]["push"]["sound"]["critical"] == 1
    assert critical["data"]["channel"] == "alarm_stream"

    # A parent taps "Seen" on the notification.
    before = len(_real(pushes[PARENT_A]))
    hass.bus.async_fire("mobile_app_notification_action", {"action": f"CHECKBABY_ACK_{config_entry.entry_id}"})
    await hass.async_block_till_done()
    await _sound(hass, freezer, 90)

    assert len(_real(pushes[PARENT_A])) == before  # no more repeats
    assert pushes[PARENT_A][-1].data["message"] == "clear_notification"
    assert [call.data["entity_id"] for call in local_alarm["off"]] == [[SIREN]]
    assert state_of(hass, config_entry, "binary_sensor", "alert_active") == "off"
    assert state_of(hass, config_entry, "sensor", "alert_level") == "critical"  # still crying

    async_fire_mqtt_message(hass, f"{BASE}/audio/crying", "OFF")
    await _sound(hass, freezer, 62)
    assert state_of(hass, config_entry, "sensor", "alert_level") == "none"
    assert state_of(hass, config_entry, "sensor", "state") == "awake"
    assert state_of(hass, config_entry, "sensor", "crying_today") != "0"


async def test_warning_goes_to_who_is_on_duty_and_snooze_action_holds_it_back(
    hass: HomeAssistant,
    mqtt_mock: MqttMockHAClient,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    pushes: Pushes,
    local_alarm: Pushes,
) -> None:
    await _start(hass, config_entry, freezer)
    select = entity_id(hass, config_entry, "select", "on_duty")
    await hass.services.async_call("select", "select_option", {"entity_id": select, "option": PARENT_B}, blocking=True)

    async_fire_mqtt_message(hass, f"{BASE}/audio/scream", "ON")
    await _sound(hass, freezer, 16)
    assert _real(pushes[PARENT_A]) == []
    assert len(_real(pushes[PARENT_B])) == 1

    hass.bus.async_fire("mobile_app_notification_action", {"action": f"CHECKBABY_SNOOZE_{config_entry.entry_id}"})
    hass.bus.async_fire("mobile_app_notification_action", {"action": "SOMETHING_ELSE"})
    await hass.async_block_till_done()
    await _sound(hass, freezer, 100)
    assert len(_real(pushes[PARENT_B])) == 1
    assert local_alarm["on"] == []


async def test_frigate_going_offline_is_reported_and_state_is_unknown(
    hass: HomeAssistant,
    mqtt_mock: MqttMockHAClient,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    pushes: Pushes,
) -> None:
    await _start(hass, config_entry, freezer)

    async_fire_mqtt_message(hass, "frigate/available", "offline")
    await _sound(hass, freezer, 4)

    assert state_of(hass, config_entry, "sensor", "state") == "unknown"
    assert state_of(hass, config_entry, "binary_sensor", "monitoring_problem") == "on"
    problems = hass.states.get(entity_id(hass, config_entry, "sensor", "monitoring_problems"))
    assert problems is not None
    assert (problems.state, problems.attributes["problems"]) == ("1", ["frigate"])
    assert "Frigate offline" in _real(pushes[PARENT_A])[0]["message"]

    async_fire_mqtt_message(hass, "frigate/available", "online")
    await _sound(hass, freezer, 4)
    assert state_of(hass, config_entry, "binary_sensor", "monitoring_problem") == "off"
    assert state_of(hass, config_entry, "sensor", "state") != "unknown"


async def test_silent_camera_is_reported_after_a_minute(
    hass: HomeAssistant,
    mqtt_mock: MqttMockHAClient,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    pushes: Pushes,
) -> None:
    await _start(hass, config_entry, freezer)
    await _sound(hass, freezer, 130)
    assert _real(pushes[PARENT_A]) == []

    await advance(hass, freezer, 64)  # no more sound levels

    assert "audio_level" in config_entry.runtime_data.coordinator.monitor.problems
    assert len(_real(pushes[PARENT_A])) == 1


async def test_bad_payloads_are_ignored(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, config_entry: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    entry = make_entry(
        place={CONF_FRIGATE_CAMERA: CAMERA, CONF_ENGINE_ID: "crib", CONF_BED_ZONE: "bed", CONF_PERSON_IS_CAREGIVER: True}
    )
    await _start(hass, entry, freezer)
    for topic, payload in (
        (f"{BASE}/audio/dBFS", "loud"),
        (f"{BASE}/person", "many"),
        ("frigate/bed/cat", ""),
        ("checkbaby/engine/crib/state", "not json"),
        ("checkbaby/engine/crib/state", json.dumps({"rate": 30})),
        ("checkbaby/engine/crib/state", json.dumps({"status": "periodic", "rate": "fast"})),
    ):
        async_fire_mqtt_message(hass, topic, payload)
    await _sound(hass, freezer, 4)
    assert state_of(hass, entry, "sensor", "state") == "asleep"
    assert state_of(hass, entry, "binary_sensor", "breathing_movement") == "unknown"


async def test_motion_person_pet_and_door(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, freezer: FrozenDateTimeFactory, pushes: Pushes
) -> None:
    entry = make_entry(
        place={
            CONF_FRIGATE_CAMERA: CAMERA,
            CONF_BED_ZONE: "bed",
            CONF_PERSON_IS_CAREGIVER: True,
            CONF_DOOR_ENTITY: "binary_sensor.door",
        }
    )
    hass.states.async_set("binary_sensor.door", "off")
    await _start(hass, entry, freezer)

    async_fire_mqtt_message(hass, f"{BASE}/motion", "ON")
    await _sound(hass, freezer, 2)
    assert state_of(hass, entry, "binary_sensor", "motion") == "on"
    assert state_of(hass, entry, "sensor", "last_motion") not in ("unknown", "unavailable")
    async_fire_mqtt_message(hass, f"{BASE}/motion", "OFF")

    async_fire_mqtt_message(hass, "frigate/bed/cat", "1")
    await _sound(hass, freezer, 2)
    assert state_of(hass, entry, "sensor", "alert_reason") == "pet_in_bed"
    async_fire_mqtt_message(hass, "frigate/bed/dog", "0")
    await _sound(hass, freezer, 2)
    assert state_of(hass, entry, "sensor", "alert_reason") == "pet_in_bed"  # the cat is still there
    async_fire_mqtt_message(hass, "frigate/bed/cat", "0")
    await _sound(hass, freezer, 2)
    assert state_of(hass, entry, "sensor", "alert_reason") == "none"

    async_fire_mqtt_message(hass, f"{BASE}/person", "1")
    await _sound(hass, freezer, 2)
    assert state_of(hass, entry, "binary_sensor", "attended") == "on"
    async_fire_mqtt_message(hass, f"{BASE}/person", "0")
    await _sound(hass, freezer, 24)
    assert state_of(hass, entry, "binary_sensor", "attended") == "off"

    hass.states.async_set("binary_sensor.door", "unavailable")
    await hass.async_block_till_done()
    assert state_of(hass, entry, "sensor", "state") != "attended"  # an unavailable contact says nothing

    hass.states.async_set("binary_sensor.door", "on")
    await hass.async_block_till_done()  # the state change itself triggers the monitor
    assert state_of(hass, entry, "sensor", "state") == "attended"
    assert state_of(hass, entry, "binary_sensor", "quiet_time") == "off"


async def test_radar_and_engine_feed_the_breathing_hint(
    hass: HomeAssistant,
    mqtt_mock: MqttMockHAClient,
    freezer: FrozenDateTimeFactory,
    pushes: Pushes,
) -> None:
    entry = make_entry(
        place={
            CONF_FRIGATE_CAMERA: CAMERA,
            CONF_ENGINE_ID: "crib",
            CONF_BREATH_RATE_ENTITY: "sensor.radar_breath",
            CONF_HEART_RATE_ENTITY: "sensor.radar_heart",
            CONF_PRESENCE_ENTITY: "binary_sensor.in_bed",
            CONF_TEMPERATURE_ENTITY: "sensor.room_temperature",
            CONF_HUMIDITY_ENTITY: "sensor.room_humidity",
        }
    )
    hass.states.async_set("sensor.radar_breath", "42")
    hass.states.async_set("sensor.radar_heart", "128")
    hass.states.async_set("binary_sensor.in_bed", "on")
    hass.states.async_set("sensor.room_temperature", "19.5")
    hass.states.async_set("sensor.room_humidity", "nan")
    await _start(hass, entry, freezer)
    async_fire_mqtt_message(hass, "checkbaby/engine/crib/availability", "online")

    async def engine(status: str, seconds: int) -> None:
        for _ in range(seconds // 2):
            payload = {"status": status, "rate": 40.0 if status == "periodic" else None, "confidence": 0.8}
            async_fire_mqtt_message(hass, "checkbaby/engine/crib/state", json.dumps(payload))
            await _sound(hass, freezer, 2)

    await engine("periodic", 20)
    assert state_of(hass, entry, "binary_sensor", "breathing_movement") == "on"
    assert state_of(hass, entry, "sensor", "breathing_rate") in ("40.0", "42.0")
    assert state_of(hass, entry, "sensor", "heart_rate") == "128.0"
    assert state_of(hass, entry, "binary_sensor", "in_bed") == "on"
    assert state_of(hass, entry, "sensor", "sleeping_bag") == "tog_2_5"

    # Both sources fall silent. The alert is off, so it is only recorded.
    hass.states.async_set("sensor.radar_breath", "0")
    await engine("no_motion", 30)
    monitor = entry.runtime_data.coordinator.monitor
    assert state_of(hass, entry, "binary_sensor", "breathing_movement") == "off"
    assert any(alert.shadow for alert in monitor.alerts.active.values())
    assert _real(pushes[PARENT_A]) == []
    assert state_of(hass, entry, "sensor", "alert_level") == "none"

    await turn_on(hass, entry, "breathing_alert")
    await engine("no_motion", 4)
    assert state_of(hass, entry, "sensor", "alert_reason") == "no_breathing"
    assert _real(pushes[PARENT_B])[-1]["data"]["push"]["sound"]["critical"] == 1

    # An unusable engine and an unavailable radar are a monitoring problem, not an alarm.
    hass.states.async_set("sensor.radar_breath", "unavailable")
    await engine("unusable", 6)
    assert state_of(hass, entry, "sensor", "alert_reason") == "monitoring_failure"
    assert state_of(hass, entry, "binary_sensor", "breathing_movement") == "unknown"
    async_fire_mqtt_message(hass, "checkbaby/engine/crib/availability", "offline")
    await _sound(hass, freezer, 2)
    assert set(monitor.problems) == {"engine", "vital_sensor"}


async def test_smoke_is_passed_through_even_when_monitoring_is_off(
    hass: HomeAssistant,
    mqtt_mock: MqttMockHAClient,
    freezer: FrozenDateTimeFactory,
    pushes: Pushes,
    local_alarm: Pushes,
) -> None:
    entry = make_entry(
        options={
            CONF_NOTIFY_SERVICES: [PARENT_A],
            CONF_LOCAL_ALARM: [SIREN],
            CONF_SMOKE_ENTITIES: ["binary_sensor.smoke"],
            CONF_INTERNET_ENTITY: "binary_sensor.internet",
        }
    )
    hass.states.async_set("binary_sensor.smoke", "off")
    hass.states.async_set("binary_sensor.internet", "off")
    await _start(hass, entry, freezer, armed=False)

    hass.states.async_set("binary_sensor.smoke", "on")
    await hass.async_block_till_done()
    await _sound(hass, freezer, 2)

    assert _real(pushes[PARENT_A])[0]["title"].startswith("ALARM")
    # The internet is down, so the local alarm does not wait a minute.
    assert len(local_alarm["on"]) == 1


async def test_audio_relay_heartbeat_and_stop_message(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, freezer: FrozenDateTimeFactory, pushes: Pushes
) -> None:
    entry = make_entry(
        place={CONF_FRIGATE_CAMERA: CAMERA, CONF_AUDIO_URL: "http://go2rtc.local/stream.mp3"},
        options={
            CONF_NOTIFY_SERVICES: [PARENT_A],
            CONF_VOX_PLAYER: "media_player.bedroom",
            CONF_HEARTBEAT_BUTTONS: ["button.deadman"],
        },
    )
    play = async_mock_service(hass, "media_player", "play_media")
    stop = async_mock_service(hass, "media_player", "media_stop")
    await _start(hass, entry, freezer)
    # Registered after setup: the integration's own buttons bring the real service.
    presses = async_mock_service(hass, "button", "press")
    await turn_on(hass, entry, "audio_relay_enabled")

    await _sound(hass, freezer, 32)
    assert presses and presses[-1].data["entity_id"] == ["button.deadman"]
    assert play == []

    await _sound(hass, freezer, 6, level=-15.0)
    assert [call.data["media_content_id"] for call in play] == ["http://go2rtc.local/stream.mp3"]
    assert state_of(hass, entry, "binary_sensor", "audio_relay") == "on"
    await _sound(hass, freezer, 64)
    assert len(stop) == 1

    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    await hass.async_block_till_done()
    assert "stopping" in _real(pushes[PARENT_A])[-1]["message"]


async def test_no_heartbeat_while_there_is_a_problem(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, freezer: FrozenDateTimeFactory, pushes: Pushes
) -> None:
    entry = make_entry(options={CONF_NOTIFY_SERVICES: [PARENT_A], CONF_HEARTBEAT_BUTTONS: ["button.deadman"]})
    await _start(hass, entry, freezer)
    presses = async_mock_service(hass, "button", "press")
    async_fire_mqtt_message(hass, "frigate/available", "offline")
    await _sound(hass, freezer, 70)
    assert presses == []


async def test_place_without_frigate_uses_entities(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, pushes: Pushes
) -> None:
    entry = make_entry(
        place={
            CONF_CRY_ENTITY: "binary_sensor.cam_cry",
            CONF_MOTION_ENTITY: "binary_sensor.cam_motion",
            CONF_LEVEL_ENTITY: "sensor.cam_level",
            CONF_CAMERA_ENTITY: "camera.nursery",
        }
    )
    hass.states.async_set("binary_sensor.cam_cry", "off")
    hass.states.async_set("binary_sensor.cam_motion", "on")
    hass.states.async_set("sensor.cam_level", "-48")
    await setup(hass, entry)
    await turn_on(hass, entry, "monitoring")
    await advance(hass, freezer, 4)
    assert state_of(hass, entry, "binary_sensor", "motion") == "on"
    assert state_of(hass, entry, "sensor", "noise_level") == "-48.0"
    assert state_of(hass, entry, "binary_sensor", "monitoring_problem") == "off"

    hass.states.async_set("binary_sensor.cam_cry", "on")
    await hass.async_block_till_done()
    await advance(hass, freezer, 16)
    assert len(_real(pushes[PARENT_A])) == 1

    hass.states.async_set("sensor.cam_level", "unavailable")
    hass.states.async_set("camera.nursery", "unavailable")
    await advance(hass, freezer, 4)
    assert set(entry.runtime_data.coordinator.monitor.problems) == {"audio_level", "camera"}


async def test_switching_the_sleep_place_resubscribes(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, freezer: FrozenDateTimeFactory, pushes: Pushes
) -> None:
    entry = make_entry(
        places=[("Crib", {CONF_FRIGATE_CAMERA: CAMERA}), ("Pram", {CONF_FRIGATE_CAMERA: "living_room"})]
    )
    await _start(hass, entry, freezer)
    select = entity_id(hass, entry, "select", "active_place")
    state = hass.states.get(select)
    assert state is not None
    assert (state.state, state.attributes["options"]) == ("Crib", ["Crib", "Pram"])

    await hass.services.async_call("select", "select_option", {"entity_id": select, "option": "Pram"}, blocking=True)
    await hass.async_block_till_done()
    async_fire_mqtt_message(hass, "frigate/available", "online")
    async_fire_mqtt_message(hass, "frigate/living_room/audio/dBFS", "-40")
    async_fire_mqtt_message(hass, f"{BASE}/audio/crying", "ON")  # the old place no longer counts
    async_fire_mqtt_message(hass, "frigate/living_room/motion", "ON")
    await advance(hass, freezer, 2)

    assert state_of(hass, entry, "select", "active_place") == "Pram"
    assert state_of(hass, entry, "binary_sensor", "crying") == "off"
    assert state_of(hass, entry, "binary_sensor", "motion") == "on"


async def test_settings_alerts_and_sleep_survive_a_reload(
    hass: HomeAssistant,
    mqtt_mock: MqttMockHAClient,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    pushes: Pushes,
) -> None:
    await _start(hass, config_entry, freezer)
    number = entity_id(hass, config_entry, "number", "cry_warning_s")
    await hass.services.async_call("number", "set_value", {"entity_id": number, "value": 30}, blocking=True)
    await _sound(hass, freezer, 20)

    assert await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()

    settings = config_entry.runtime_data.coordinator.settings
    assert (settings.armed, settings.cry_warning_s) == (True, 30.0)
    assert state_of(hass, config_entry, "switch", "monitoring") == "on"
    assert state_of(hass, config_entry, "number", "cry_warning_s") == "30.0"
    assert config_entry.runtime_data.coordinator.monitor.sleep_log.sessions


async def test_downtime_while_armed_is_reported_after_restart(
    hass: HomeAssistant,
    mqtt_mock: MqttMockHAClient,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    pushes: Pushes,
    hass_storage: dict[str, Any],
) -> None:
    hass_storage[f"{DOMAIN}.{config_entry.entry_id}"] = {
        "version": 1,
        "minor_version": 1,
        "key": f"{DOMAIN}.{config_entry.entry_id}",
        "data": {"settings": {"armed": True}, "last_alive": dt_util.utcnow().timestamp() - 600},
    }
    await _start(hass, config_entry, freezer, armed=False)
    await _sound(hass, freezer, 2)

    messages = [push["message"] for push in _real(pushes[PARENT_A])]
    assert any("interrupted for 10 min" in message for message in messages)


async def test_state_is_saved_while_running_and_the_local_alarm_is_remembered(
    hass: HomeAssistant,
    mqtt_mock: MqttMockHAClient,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    pushes: Pushes,
    local_alarm: Pushes,
    hass_storage: dict[str, Any],
) -> None:
    key = f"{DOMAIN}.{config_entry.entry_id}"
    await _start(hass, config_entry, freezer)
    await _call_test_alert(hass)
    await _sound(hass, freezer, 80)

    # Saved by the running monitor, not only on shutdown.
    stored = hass_storage[key]["data"]
    assert stored["settings"]["armed"] is True
    assert stored["last_alive"] == pytest.approx(dt_util.utcnow().timestamp(), abs=20)
    assert stored["local_alarm_on"] is True
    assert len(local_alarm["on"]) == 1

    # After a restart the alarm that was left on can still be switched off.
    assert await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()
    hass.bus.async_fire("mobile_app_notification_action", {"action": f"CHECKBABY_ACK_{config_entry.entry_id}"})
    await hass.async_block_till_done()
    await _sound(hass, freezer, 2)
    assert len(local_alarm["off"]) == 1


async def _call_test_alert(hass: HomeAssistant) -> None:
    await hass.services.async_call(DOMAIN, "test_alert", {}, blocking=True)


async def test_without_a_sleep_place_the_state_is_unknown_and_reported(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, pushes: Pushes
) -> None:
    entry = make_entry(places=[])
    await setup(hass, entry)
    await turn_on(hass, entry, "monitoring")
    await advance(hass, freezer, 4)

    assert state_of(hass, entry, "sensor", "state") == "unknown"
    assert entry.runtime_data.coordinator.monitor.problems == ["sleep_place"]
    assert "no sleep place" in _real(pushes[PARENT_A])[0]["message"]


async def test_unavailable_crying_sensor_is_a_problem(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, pushes: Pushes
) -> None:
    entry = make_entry(place={CONF_CRY_ENTITY: "binary_sensor.cam_cry"})
    hass.states.async_set("binary_sensor.cam_cry", "off")
    await setup(hass, entry)
    await turn_on(hass, entry, "monitoring")
    await advance(hass, freezer, 4)
    assert state_of(hass, entry, "sensor", "state") == "asleep"

    hass.states.async_set("binary_sensor.cam_cry", "unavailable")
    await advance(hass, freezer, 4)
    assert state_of(hass, entry, "sensor", "state") == "unknown"
    assert entry.runtime_data.coordinator.monitor.problems == ["cry_sensor"]


async def test_mqtt_that_comes_up_later_is_subscribed(
    hass: HomeAssistant,
    mqtt_mock: MqttMockHAClient,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    pushes: Pushes,
) -> None:
    # MQTT is not loaded yet when CheckBaby starts.
    with patch.object(CheckBabyCoordinator, "_mqtt_available", return_value=False):
        await setup(hass, config_entry)
        coordinator = config_entry.runtime_data.coordinator
        await turn_on(hass, config_entry, "monitoring")
        await advance(hass, freezer, 2)
        async_fire_mqtt_message(hass, f"{BASE}/audio/crying", "ON")
        await advance(hass, freezer, 2)
        assert "mqtt" in coordinator.monitor.problems
        assert state_of(hass, config_entry, "binary_sensor", "crying") == "off"

    await advance(hass, freezer, 4)
    async_fire_mqtt_message(hass, f"{BASE}/audio/crying", "ON")
    await advance(hass, freezer, 2)

    assert state_of(hass, config_entry, "binary_sensor", "crying") == "on"
    assert "mqtt" not in coordinator.monitor.problems


async def test_local_alarm_goes_off_when_a_snoozed_alert_ends(
    hass: HomeAssistant,
    mqtt_mock: MqttMockHAClient,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    pushes: Pushes,
    local_alarm: Pushes,
) -> None:
    await _start(hass, config_entry, freezer)
    async_fire_mqtt_message(hass, f"{BASE}/audio/crying", "ON")
    await _sound(hass, freezer, 80)
    assert len(local_alarm["on"]) == 1

    hass.bus.async_fire("mobile_app_notification_action", {"action": f"CHECKBABY_SNOOZE_{config_entry.entry_id}"})
    await hass.async_block_till_done()
    await _sound(hass, freezer, 2)
    assert len(local_alarm["off"]) == 1  # quiet means quiet

    async_fire_mqtt_message(hass, f"{BASE}/audio/crying", "OFF")
    await _sound(hass, freezer, 70)
    assert state_of(hass, config_entry, "sensor", "alert_level") == "none"
    assert config_entry.runtime_data.coordinator.notifier.local_on is False
    assert len(local_alarm["on"]) == 1


async def test_frigate_camera_wins_over_mapped_entities_and_fahrenheit_is_converted(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, freezer: FrozenDateTimeFactory, pushes: Pushes
) -> None:
    entry = make_entry(
        place={
            CONF_FRIGATE_CAMERA: CAMERA,
            CONF_CRY_ENTITY: "binary_sensor.cam_cry",
            CONF_MOTION_ENTITY: "binary_sensor.cam_motion",
            CONF_LEVEL_ENTITY: "sensor.cam_level",
            CONF_TEMPERATURE_ENTITY: "sensor.room_temperature",
        }
    )
    hass.states.async_set("binary_sensor.cam_cry", "off")
    hass.states.async_set("binary_sensor.cam_motion", "off")
    hass.states.async_set("sensor.cam_level", "-10")
    hass.states.async_set("sensor.room_temperature", "68", {"unit_of_measurement": "°F"})
    await _start(hass, entry, freezer)

    async_fire_mqtt_message(hass, f"{BASE}/audio/crying", "ON")
    async_fire_mqtt_message(hass, f"{BASE}/motion", "ON")
    await _sound(hass, freezer, 4)

    assert state_of(hass, entry, "binary_sensor", "crying") == "on"  # not overwritten by the entity
    assert state_of(hass, entry, "binary_sensor", "motion") == "on"
    assert float(state_of(hass, entry, "sensor", "noise_level")) < -40
    assert entry.runtime_data.coordinator.monitor.signals.temperature == pytest.approx(20.0)
    assert state_of(hass, entry, "sensor", "sleeping_bag") == "tog_2_5"


async def test_constant_level_from_an_entity_is_not_a_dead_microphone(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, pushes: Pushes
) -> None:
    entry = make_entry(place={CONF_CRY_ENTITY: "binary_sensor.cam_cry", CONF_LEVEL_ENTITY: "sensor.cam_level"})
    hass.states.async_set("binary_sensor.cam_cry", "off")
    hass.states.async_set("sensor.cam_level", "-40")
    await setup(hass, entry)
    await turn_on(hass, entry, "monitoring")
    await advance(hass, freezer, 700, step=10)
    assert entry.runtime_data.coordinator.monitor.problems == []


async def test_radar_that_stops_reporting_is_a_problem_not_continued_breathing(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, freezer: FrozenDateTimeFactory, pushes: Pushes
) -> None:
    entry = make_entry(place={CONF_FRIGATE_CAMERA: CAMERA, CONF_BREATH_RATE_ENTITY: "sensor.radar_breath"})
    hass.states.async_set("sensor.radar_breath", "42")
    await _start(hass, entry, freezer)
    await _sound(hass, freezer, 60)
    assert state_of(hass, entry, "binary_sensor", "breathing_movement") == "on"

    await _sound(hass, freezer, 64)  # the sensor still shows 42 but has not reported for two minutes

    assert state_of(hass, entry, "binary_sensor", "breathing_movement") == "unknown"
    assert entry.runtime_data.coordinator.monitor.problems == ["vital_sensor"]

    hass.states.async_set("sensor.radar_breath", "41")
    await _sound(hass, freezer, 2)
    assert state_of(hass, entry, "binary_sensor", "breathing_movement") == "on"


async def test_issues_for_missing_mqtt_targets_and_places(hass: HomeAssistant) -> None:
    entry = make_entry(options={}, places=[])
    await setup(hass, entry)
    registry = ir.async_get(hass)
    assert registry.async_get_issue(DOMAIN, f"no_alert_target_{entry.entry_id}") is not None
    assert registry.async_get_issue(DOMAIN, f"no_sleep_place_{entry.entry_id}") is not None
    assert state_of(hass, entry, "select", "active_place") == "unknown"

    needs_mqtt = make_entry()
    needs_mqtt = MockConfigEntry(
        domain=DOMAIN, title="Zwei", unique_id="zwei", data=dict(needs_mqtt.data),
        options=dict(needs_mqtt.options), subentries_data=[
            {"data": dict(s.data), "subentry_type": s.subentry_type, "title": s.title, "unique_id": None}
            for s in needs_mqtt.subentries.values()
        ],
    )  # fmt: skip
    await setup(hass, needs_mqtt)
    assert registry.async_get_issue(DOMAIN, f"mqtt_missing_{needs_mqtt.entry_id}") is not None
    assert registry.async_get_issue(DOMAIN, f"no_alert_target_{needs_mqtt.entry_id}") is None
    assert "mqtt" in needs_mqtt.runtime_data.coordinator.monitor.watchdog.problems(dt_util.utcnow().timestamp())

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert registry.async_get_issue(DOMAIN, f"no_alert_target_{entry.entry_id}") is None


@pytest.mark.parametrize("missing", [PARENT_A])
async def test_missing_notify_service_is_a_monitoring_problem(
    hass: HomeAssistant,
    mqtt_mock: MqttMockHAClient,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    missing: str,
) -> None:
    reachable = async_mock_service(hass, "notify", PARENT_B)
    await _start(hass, config_entry, freezer)
    await _sound(hass, freezer, 4)
    assert config_entry.runtime_data.coordinator.monitor.problems == ["notify"]
    # The phone that still exists is told about it.
    assert "notification target is missing" in _real(reachable)[0]["message"]


async def test_failing_helpers_do_not_stop_the_alert_chain(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, freezer: FrozenDateTimeFactory, pushes: Pushes
) -> None:
    entry = make_entry(
        place={CONF_FRIGATE_CAMERA: CAMERA, CONF_AUDIO_URL: "http://go2rtc.local/stream.mp3"},
        options={
            CONF_NOTIFY_SERVICES: [PARENT_A, PARENT_B],
            CONF_LOCAL_ALARM: [SIREN],
            CONF_HEARTBEAT_BUTTONS: ["button.deadman"],
        },
    )

    async def broken(call: ServiceCall) -> None:
        raise RuntimeError("device offline")

    await _start(hass, entry, freezer)
    await turn_on(hass, entry, "audio_relay_enabled")  # no speaker configured: the relay does nothing
    hass.services.async_register("homeassistant", "turn_on", broken)
    hass.services.async_register("button", "press", broken)
    hass.services.async_register("notify", PARENT_A, broken)
    delivered = async_mock_service(hass, "notify", PARENT_B)

    async_fire_mqtt_message(hass, f"{BASE}/audio/crying", "ON")
    await _sound(hass, freezer, 80, level=-15.0)

    assert len(_real(delivered)) == 1
    assert state_of(hass, entry, "sensor", "alert_reason") == "crying"
