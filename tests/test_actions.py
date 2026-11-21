"""Entities that change settings, buttons, actions, the AI assessment, diagnostics."""

from __future__ import annotations

import asyncio
from typing import Any

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_mqtt_message,
    async_mock_service,
)
from pytest_homeassistant_custom_component.typing import MqttMockHAClient

from custom_components.checkbaby import coordinator as coordinator_module
from custom_components.checkbaby.const import (
    CONF_AI_BUDGET,
    CONF_AI_CONSENT,
    CONF_AI_ENTITIES,
    CONF_BABYSITTER_SERVICE,
    CONF_BIRTH_DATE,
    CONF_CAMERA_ENTITY,
    CONF_CHILD_NAME,
    CONF_CRY_ENTITY,
    CONF_NOTIFY_SERVICES,
    DOMAIN,
)
from custom_components.checkbaby.diagnostics import async_get_config_entry_diagnostics

from .conftest import (
    CAMERA,
    PARENT_A,
    PARENT_B,
    advance,
    entity_id,
    make_entry,
    notices,
    setup,
    state_of,
    turn_on,
)
from .test_monitoring import _real, _sound, _start

Pushes = dict[str, list[ServiceCall]]

GOOD_ANSWER = {
    "presence": "in_bed",
    "position": "supine",
    "face_visible": True,
    "airway_risk": "none",
    "state": "asleep",
    "hazards": "",
    "view_ok": True,
    "assessment": "ok",
    "confidence": 0.9,
    "reason": "Sleeping on the back.",
}
AI_OPTIONS = {
    CONF_NOTIFY_SERVICES: [PARENT_A, PARENT_B],
    CONF_AI_ENTITIES: ["ai_task.cloud", "ai_task.local"],
    CONF_AI_CONSENT: True,
}


# A sleep place that needs no MQTT, for tests that run on real time.
ENTITY_PLACE = {CONF_CRY_ENTITY: "binary_sensor.cam_cry", CONF_CAMERA_ENTITY: "camera.nursery"}


class FakeAI:
    """Stands in for ai_task.generate_data."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.calls: list[dict[str, Any]] = []
        self.answers: dict[str, Any] = {}
        hass.services.async_register(
            "ai_task", "generate_data", self._handle, supports_response=SupportsResponse.ONLY
        )

    async def _handle(self, call: ServiceCall) -> ServiceResponse:
        self.calls.append(dict(call.data))
        answer = self.answers.get(call.data["entity_id"], GOOD_ANSWER)
        if isinstance(answer, Exception):
            raise answer
        if answer == "slow":
            await asyncio.sleep(0.3)
            answer = GOOD_ANSWER
        return {"conversation_id": "x", "data": answer}


async def _call(hass: HomeAssistant, service: str, data: dict[str, Any] | None = None) -> Any:
    responds = service in ("assess_now", "quick_check", "night_report")
    return await hass.services.async_call(DOMAIN, service, data or {}, blocking=True, return_response=responds)


# -- settings entities -----------------------------------------------------


async def test_switches_numbers_and_selects_change_settings(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, config_entry: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    await _start(hass, config_entry, freezer, armed=False)
    settings = config_entry.runtime_data.coordinator.settings
    assert state_of(hass, config_entry, "switch", "monitoring") == "off"
    assert state_of(hass, config_entry, "binary_sensor", "quiet_time") == "off"

    for key in ("monitoring", "privacy_mode", "ai_assessment_enabled", "breathing_alert", "audio_relay_enabled"):
        await turn_on(hass, config_entry, key)
    assert (settings.armed, settings.privacy, settings.ai_enabled, settings.breathing_alert, settings.vox_enabled) == (
        True, True, True, True, True,
    )  # fmt: skip
    assert state_of(hass, config_entry, "sensor", "state") == "unknown"  # privacy mode
    privacy = entity_id(hass, config_entry, "switch", "privacy_mode")
    await hass.services.async_call("switch", "turn_off", {"entity_id": privacy}, blocking=True)
    await _sound(hass, freezer, 2)
    assert settings.privacy is False
    assert state_of(hass, config_entry, "binary_sensor", "quiet_time") == "on"

    for key, value, field in (
        ("cry_critical_s", 240, "cry_critical_s"),
        ("noise_margin_db", 12, "noise_margin_db"),
        ("no_breathing_s", 25, "no_breathing_s"),
        ("ai_interval_min", 5, "ai_interval_min"),
        ("temp_min", 17, "temp_min"),
        ("temp_max", 23.5, "temp_max"),
    ):
        number = entity_id(hass, config_entry, "number", key)
        await hass.services.async_call("number", "set_value", {"entity_id": number, "value": value}, blocking=True)
        assert getattr(settings, field) == value
    lowest = hass.states.get(entity_id(hass, config_entry, "number", "no_breathing_s"))
    assert lowest is not None
    assert lowest.attributes["min"] == 20  # never below normal newborn breathing pauses

    for key, option in (("mode", "babysitter"), ("sensitivity", "high"), ("vital_fusion", "any")):
        select = entity_id(hass, config_entry, "select", key)
        await hass.services.async_call("select", "select_option", {"entity_id": select, "option": option}, blocking=True)
        assert state_of(hass, config_entry, "select", key) == option
    assert (settings.mode.value, settings.sensitivity.value, settings.vital_fusion.value) == (
        "babysitter", "high", "any",
    )  # fmt: skip

    on_duty = hass.states.get(entity_id(hass, config_entry, "select", "on_duty"))
    assert on_duty is not None
    assert (on_duty.state, on_duty.attributes["options"]) == ("all", ["all", PARENT_A, PARENT_B])
    settings.on_duty = "mobile_app_gone"
    await _sound(hass, freezer, 2)
    assert state_of(hass, config_entry, "select", "on_duty") == "all"
    assert state_of(hass, config_entry, "sensor", "age_profile") == "newborn"


async def test_babysitter_gets_alerts_only_in_babysitter_mode(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, freezer: FrozenDateTimeFactory, pushes: Pushes
) -> None:
    entry = make_entry(options={CONF_NOTIFY_SERVICES: [PARENT_A], CONF_BABYSITTER_SERVICE: PARENT_B})
    await _start(hass, entry, freezer)
    await _call(hass, "test_alert", {"level": "warning"})
    await _sound(hass, freezer, 2)
    assert (len(_real(pushes[PARENT_A])), len(_real(pushes[PARENT_B]))) == (1, 0)
    await _call(hass, "acknowledge")

    select = entity_id(hass, entry, "select", "mode")
    await hass.services.async_call("select", "select_option", {"entity_id": select, "option": "babysitter"}, blocking=True)
    await _call(hass, "test_alert", {"level": "warning"})
    await _sound(hass, freezer, 2)
    assert len(_real(pushes[PARENT_B])) == 1


async def test_several_babysitters_are_told(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, freezer: FrozenDateTimeFactory, pushes: Pushes
) -> None:
    granny = async_mock_service(hass, "notify", "mobile_app_granny")
    entry = make_entry(
        options={CONF_NOTIFY_SERVICES: [PARENT_A], CONF_BABYSITTER_SERVICE: [PARENT_B, "mobile_app_granny", PARENT_A]}
    )
    await _start(hass, entry, freezer)
    select = entity_id(hass, entry, "select", "mode")
    await hass.services.async_call("select", "select_option", {"entity_id": select, "option": "babysitter"}, blocking=True)
    await _call(hass, "test_alert", {"level": "warning"})
    await _sound(hass, freezer, 2)
    # Everyone once, also the parent who is listed twice.
    assert (len(_real(pushes[PARENT_A])), len(_real(pushes[PARENT_B])), len(_real(granny))) == (1, 1, 1)


# -- buttons and actions ---------------------------------------------------


async def test_buttons(
    hass: HomeAssistant,
    mqtt_mock: MqttMockHAClient,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    pushes: Pushes,
) -> None:
    await _start(hass, config_entry, freezer)

    async def press(key: str) -> None:
        button = entity_id(hass, config_entry, "button", key)
        await hass.services.async_call("button", "press", {"entity_id": button}, blocking=True)
        await _sound(hass, freezer, 2)

    await press("test_alert")
    assert state_of(hass, config_entry, "sensor", "alert_reason") == "test"
    assert _real(pushes[PARENT_A])[-1]["data"]["push"]["sound"]["critical"] == 1
    await press("acknowledge")
    assert state_of(hass, config_entry, "sensor", "alert_reason") == "none"

    await press("snooze")
    settings = config_entry.runtime_data.coordinator.settings
    assert settings.snooze_until > 0

    # Every button shows what it did, on the phone and in Home Assistant's notifications.
    await press("quick_check")
    assert "Testkind: asleep." in _real(pushes[PARENT_A])[-1]["message"]
    assert notices(hass)["quick_check"].startswith("Testkind: asleep.")
    await press("night_report")
    assert "Testkind" in _real(pushes[PARENT_B])[-1]["message"]
    assert notices(hass)["night_report"].startswith("Testkind")
    await press("assess_now")  # no AI configured: it says so
    assert state_of(hass, config_entry, "sensor", "ai_assessment") == "unknown"
    assert notices(hass)["ai_check"].startswith("No AI check: no AI task is chosen.")
    assert _real(pushes[PARENT_A])[-1]["data"]["tag"].endswith("_ai_check")


async def test_actions_return_data(
    hass: HomeAssistant,
    mqtt_mock: MqttMockHAClient,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    pushes: Pushes,
) -> None:
    await _start(hass, config_entry, freezer)
    await _sound(hass, freezer, 60)

    check = await _call(hass, "quick_check", {"notify": True})
    assert (check["state"], check["alert_level"], check["alert"]) == ("asleep", "none", None)
    assert check["asleep_minutes"] == 1
    assert check["summary"].startswith("Testkind: asleep.")
    assert _real(pushes[PARENT_A])[-1]["message"] == check["summary"]

    await _call(hass, "end_sleep", {"config_entry_id": config_entry.entry_id})
    assert state_of(hass, config_entry, "sensor", "state") == "awake"
    await _call(hass, "start_sleep")
    assert state_of(hass, config_entry, "sensor", "state") == "asleep"

    report = await _call(hass, "night_report", {"notify": True})
    assert report["wakeups"] == 1
    assert report["sleep_phases"] == 1
    assert report["slept_seconds"] > 0
    assert _real(pushes[PARENT_A])[-1]["message"] == report["summary"]

    await _call(hass, "snooze", {"minutes": 10})
    snoozed = config_entry.runtime_data.coordinator.settings.snooze_until
    assert snoozed == pytest.approx(coordinator_module.dt_util.utcnow().timestamp() + 600, abs=3)
    assert await _call(hass, "assess_now") == {"assessment": None}


async def test_actions_need_an_unambiguous_child(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    with pytest.raises(ServiceValidationError):
        await _call(hass, "acknowledge")  # nothing is set up

    await setup(hass, config_entry)
    second = MockConfigEntry(
        domain=DOMAIN, title="Zwei", unique_id="zwei", data={CONF_CHILD_NAME: "Zwei", CONF_BIRTH_DATE: "2027-02-14"},
        options={CONF_NOTIFY_SERVICES: [PARENT_A]},
    )  # fmt: skip
    await setup(hass, second)

    with pytest.raises(ServiceValidationError):
        await _call(hass, "acknowledge")
    with pytest.raises(ServiceValidationError):
        await _call(hass, "acknowledge", {"config_entry_id": "nope"})
    await _call(hass, "test_alert", {"config_entry_id": second.entry_id})
    assert state_of(hass, second, "sensor", "alert_reason") == "test"
    assert state_of(hass, config_entry, "sensor", "alert_reason") == "none"


# -- AI assessment -----------------------------------------------------------


async def test_ai_assessment_end_to_end(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, freezer: FrozenDateTimeFactory, pushes: Pushes
) -> None:
    entry = make_entry(options=AI_OPTIONS)
    ai = FakeAI(hass)
    await _start(hass, entry, freezer)
    await turn_on(hass, entry, "ai_assessment_enabled")

    result = await _call(hass, "assess_now")
    await hass.async_block_till_done()

    assert result["assessment"]["position"] == "supine"
    call = ai.calls[0]
    assert call["entity_id"] == "ai_task.cloud"
    assert call["attachments"][0]["media_content_id"] == "media-source://camera/camera.nursery"
    assert set(call["structure"]) >= {"position", "airway_risk", "confidence"}
    assert "newborn" in call["instructions"]
    assert state_of(hass, entry, "sensor", "ai_assessment") == "ok"
    assert state_of(hass, entry, "sensor", "position") == "supine"
    assert state_of(hass, entry, "binary_sensor", "ai_available") == "on"
    assert state_of(hass, entry, "sensor", "ai_calls_last_hour") == "1"
    attributes = hass.states.get(entity_id(hass, entry, "sensor", "ai_assessment"))
    assert attributes is not None
    assert attributes.attributes["reason"] == "Sleeping on the back."


async def test_ai_warning_is_rechecked_and_only_then_critical(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, freezer: FrozenDateTimeFactory, pushes: Pushes
) -> None:
    entry = make_entry(options=AI_OPTIONS)
    ai = FakeAI(hass)
    ai.answers["ai_task.cloud"] = {**GOOD_ANSWER, "airway_risk": "likely", "assessment": "critical"}
    await _start(hass, entry, freezer)
    await turn_on(hass, entry, "ai_assessment_enabled")

    await _call(hass, "assess_now")
    await _sound(hass, freezer, 2)
    assert state_of(hass, entry, "sensor", "alert_reason") == "airway_risk"
    assert state_of(hass, entry, "sensor", "alert_level") == "warning"
    assert len(ai.calls) == 1

    await _sound(hass, freezer, 18)  # the second look happens by itself
    assert len(ai.calls) == 2
    assert state_of(hass, entry, "sensor", "alert_level") == "critical"
    assert _real(pushes[PARENT_B])[-1]["title"].startswith("ALARM")


async def test_ai_falls_back_to_the_next_task_and_reports_total_failure(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, freezer: FrozenDateTimeFactory, pushes: Pushes
) -> None:
    entry = make_entry(options=AI_OPTIONS)
    ai = FakeAI(hass)
    ai.answers["ai_task.cloud"] = HomeAssistantError("quota exceeded")
    await _start(hass, entry, freezer)

    result = await _call(hass, "quick_check", {"with_ai": True})
    assert [call["entity_id"] for call in ai.calls] == ["ai_task.cloud", "ai_task.local"]
    assert result["assessment"] == "ok"
    assert result["assessment_reason"] == "Sleeping on the back."

    ai.answers["ai_task.local"] = {"nonsense": True}
    assert await _call(hass, "assess_now") == {"assessment": None}
    await hass.async_block_till_done()
    assert state_of(hass, entry, "binary_sensor", "ai_available") == "off"
    # A failed AI is not an alert and changes nothing else.
    assert state_of(hass, entry, "sensor", "alert_level") == "none"


async def test_ai_timeout_counts_as_no_answer(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
    # No frozen clock here: the timeout has to run on real time.
    monkeypatch.setattr(coordinator_module, "AI_TIMEOUT_SECONDS", 0.01)
    entry = make_entry(place=ENTITY_PLACE, options={**AI_OPTIONS, CONF_AI_ENTITIES: ["ai_task.cloud"]})
    ai = FakeAI(hass)
    ai.answers["ai_task.cloud"] = "slow"
    await setup(hass, entry)

    assert await _call(hass, "assess_now") == {"assessment": None}
    assert entry.runtime_data.coordinator.monitor.ai_available is False
    await asyncio.sleep(0.35)  # let the abandoned call finish


async def test_assessment_is_refused_while_one_runs_or_the_budget_is_spent(hass: HomeAssistant) -> None:
    entry = make_entry(place=ENTITY_PLACE, options={**AI_OPTIONS, CONF_AI_BUDGET: 1})
    ai = FakeAI(hass)
    ai.answers["ai_task.cloud"] = "slow"
    await setup(hass, entry)
    coordinator = entry.runtime_data.coordinator

    running = hass.async_create_task(coordinator.async_assess("routine"))
    await asyncio.sleep(0.05)
    assert await coordinator.async_assess("manual", manual=True) is None  # one at a time
    assert await running is not None
    assert await coordinator.async_assess("routine") is None  # budget of one per hour is spent
    assert len(ai.calls) == 1


async def test_routine_ai_checks_respect_switch_consent_and_budget(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, freezer: FrozenDateTimeFactory, pushes: Pushes
) -> None:
    entry = make_entry(options={**AI_OPTIONS, CONF_AI_BUDGET: 2})
    ai = FakeAI(hass)
    await _start(hass, entry, freezer)
    number = entity_id(hass, entry, "number", "ai_interval_min")
    await hass.services.async_call("number", "set_value", {"entity_id": number, "value": 2}, blocking=True)

    switch = entity_id(hass, entry, "switch", "ai_assessment_enabled")
    assert state_of(hass, entry, "switch", "ai_assessment_enabled") == "on"  # on unless paused
    await hass.services.async_call("switch", "turn_off", {"entity_id": switch}, blocking=True)
    await _sound(hass, freezer, 130)
    assert ai.calls == []  # paused

    await turn_on(hass, entry, "ai_assessment_enabled")
    await _sound(hass, freezer, 400)
    assert len(ai.calls) == 2  # the hourly budget stops the third


async def test_privacy_mode_blocks_even_a_manual_ai_check(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, freezer: FrozenDateTimeFactory
) -> None:
    entry = make_entry(options=AI_OPTIONS)
    ai = FakeAI(hass)
    await _start(hass, entry, freezer)
    await turn_on(hass, entry, "privacy_mode")

    assert await _call(hass, "assess_now") == {"assessment": None}
    await _call(hass, "quick_check", {"with_ai": True})
    button = entity_id(hass, entry, "button", "assess_now")
    await hass.services.async_call("button", "press", {"entity_id": button}, blocking=True)
    assert ai.calls == []  # no image leaves the house
    assert "privacy mode is on" in notices(hass)["ai_check"]


async def test_ai_check_button_shows_the_answer_or_why_there_is_none(hass: HomeAssistant, pushes: Pushes) -> None:
    entry = make_entry(place=ENTITY_PLACE, options=AI_OPTIONS)
    ai = FakeAI(hass)
    await setup(hass, entry)
    coordinator = entry.runtime_data.coordinator
    button = entity_id(hass, entry, "button", "assess_now")

    async def press() -> str:
        await hass.services.async_call("button", "press", {"entity_id": button}, blocking=True)
        return notices(hass)["ai_check"]

    assert await press() == "Looks fine (90 % sure). Sleeping on the back."
    assert _real(pushes[PARENT_A])[-1]["message"] == "Looks fine (90 % sure). Sleeping on the back."

    ai.answers = {"ai_task.cloud": HomeAssistantError("quota exceeded"), "ai_task.local": {"nonsense": True}}
    assert await press() == "The AI gave no usable answer: ai_task.local: unusable answer"

    ai.answers = {"ai_task.cloud": "slow"}
    running = hass.async_create_task(coordinator.async_assess("manual", manual=True))
    await asyncio.sleep(0.05)
    assert await press() == "An AI check is already running."
    await running


@pytest.mark.parametrize(
    ("place", "options", "said"),
    [
        (ENTITY_PLACE, {**AI_OPTIONS, CONF_AI_CONSENT: False}, "sending pictures is not confirmed"),
        ({CONF_CRY_ENTITY: "binary_sensor.cam_cry"}, AI_OPTIONS, "no camera entity"),
    ],
)
async def test_ai_check_button_names_what_is_missing(
    hass: HomeAssistant, pushes: Pushes, place: dict[str, Any], options: dict[str, Any], said: str
) -> None:
    entry = make_entry(place=place, options=options)
    FakeAI(hass)
    await setup(hass, entry)
    button = entity_id(hass, entry, "button", "assess_now")
    await hass.services.async_call("button", "press", {"entity_id": button}, blocking=True)
    assert said in notices(hass)["ai_check"]


async def test_no_ai_calls_without_consent(
    hass: HomeAssistant, mqtt_mock: MqttMockHAClient, freezer: FrozenDateTimeFactory
) -> None:
    entry = make_entry(options={**AI_OPTIONS, CONF_AI_CONSENT: False})
    ai = FakeAI(hass)
    await _start(hass, entry, freezer)
    await turn_on(hass, entry, "ai_assessment_enabled")
    await _sound(hass, freezer, 700)
    assert await _call(hass, "assess_now") == {"assessment": None}
    assert ai.calls == []


# -- setup, unload, diagnostics ----------------------------------------------


async def test_unload_and_invalid_birth_date(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data.coordinator
    snapshot = coordinator.data
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED
    coordinator.async_refresh_now()  # a late callback after unload does nothing
    assert coordinator.data is snapshot

    broken = make_entry(birth_date="not-a-date")
    broken = MockConfigEntry(domain=DOMAIN, title="Kaputt", data=dict(broken.data))
    broken.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(broken.entry_id)
    assert broken.state is ConfigEntryState.SETUP_ERROR


@pytest.mark.parametrize(("today", "expected"), [("2027-03-01", "newborn"), ("2027-06-01", "infant"), ("2028-03-01", "toddler")])
async def test_age_profile_follows_the_date(
    hass: HomeAssistant, config_entry: MockConfigEntry, freezer: FrozenDateTimeFactory, today: str, expected: str
) -> None:
    freezer.move_to(f"{today} 12:00:00")
    await setup(hass, config_entry)
    assert state_of(hass, config_entry, "sensor", "age_profile") == expected


async def test_age_profile_changes_overnight(
    hass: HomeAssistant, config_entry: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    await hass.config.async_set_time_zone("UTC")
    freezer.move_to("2027-05-15 23:59:00+00:00")  # born 2027-02-14; day 91 is 2027-05-16
    await setup(hass, config_entry)
    assert state_of(hass, config_entry, "sensor", "age_profile") == "newborn"
    await advance(hass, freezer, 122, step=61)
    assert state_of(hass, config_entry, "sensor", "age_profile") == "infant"


async def test_diagnostics_leave_out_the_childs_details(
    hass: HomeAssistant,
    mqtt_mock: MqttMockHAClient,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    pushes: Pushes,
) -> None:
    await _start(hass, config_entry, freezer)
    async_fire_mqtt_message(hass, f"frigate/{CAMERA}/audio/crying", "ON")
    await _sound(hass, freezer, 20)

    data = await async_get_config_entry_diagnostics(hass, config_entry)

    assert data["entry"] == {CONF_CHILD_NAME: "**REDACTED**", CONF_BIRTH_DATE: "**REDACTED**"}
    assert "Testkind" not in str(data)
    assert data["snapshot"]["state"] == "crying"
    assert data["snapshot"]["alert_kind"] == "crying"
    assert data["settings"]["armed"] is True
    assert any(event["type"] == "alert" for event in data["events"])
    assert data["places"][0]["frigate_camera"] == CAMERA
