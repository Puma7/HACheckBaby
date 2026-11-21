"""Config flow, options flow and the sleep place sub-entries."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.checkbaby.const import (
    CONF_ACKNOWLEDGED,
    CONF_AI_CONSENT,
    CONF_AI_ENTITIES,
    CONF_BIRTH_DATE,
    CONF_CHILD_NAME,
    CONF_CRY_ENTITY,
    CONF_DOOR_ENTITY,
    CONF_FRIGATE_CAMERA,
    CONF_LOCAL_ALARM,
    CONF_NOTIFY_SERVICES,
    CONF_PLACE_NAME,
    CONF_SMOKE_ENTITIES,
    CONF_VOX_PLAYER,
    DOMAIN,
    SUBENTRY_PLACE,
)

from .conftest import PARENT_A, setup

USER_INPUT = {CONF_CHILD_NAME: "  Testkind ", CONF_BIRTH_DATE: "2027-02-14"}
PLACE_INPUT = {CONF_PLACE_NAME: " Crib ", CONF_FRIGATE_CAMERA: "nursery"}
NOTIFY_INPUT = {CONF_NOTIFY_SERVICES: [PARENT_A]}


async def _to_step(hass: HomeAssistant, *inputs: dict[str, Any]) -> Any:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    for user_input in inputs:
        result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input)
    return result


async def test_flow_creates_child_with_place_and_targets(hass: HomeAssistant) -> None:
    result = await _to_step(hass)
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "user")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["step_id"] == "place"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], PLACE_INPUT)
    assert result["step_id"] == "notify"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], NOTIFY_INPUT)
    assert result["step_id"] == "ai"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_AI_ENTITIES: ["ai_task.gemini"], CONF_AI_CONSENT: False}
    )
    assert (result["step_id"], result["errors"]) == ("ai", {CONF_AI_CONSENT: "ai_consent_required"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_AI_ENTITIES: ["ai_task.gemini"], CONF_AI_CONSENT: True}
    )
    assert result["step_id"] == "disclaimer"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_ACKNOWLEDGED: True})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Testkind"
    assert result["data"] == {CONF_CHILD_NAME: "Testkind", CONF_BIRTH_DATE: "2027-02-14"}
    entry = result["result"]
    assert entry.unique_id == "testkind"
    assert entry.options[CONF_NOTIFY_SERVICES] == [PARENT_A]
    assert (entry.options[CONF_AI_ENTITIES], entry.options[CONF_AI_CONSENT]) == (["ai_task.gemini"], True)
    places = list(entry.subentries.values())
    assert [(place.subentry_type, place.title) for place in places] == [(SUBENTRY_PLACE, "Crib")]
    assert places[0].data[CONF_FRIGATE_CAMERA] == "nursery"
    assert CONF_PLACE_NAME not in places[0].data


async def test_no_entry_without_acknowledgement(hass: HomeAssistant) -> None:
    # The AI page is left empty: the assessment is optional.
    result = await _to_step(hass, USER_INPUT, PLACE_INPUT, NOTIFY_INPUT, {}, {CONF_ACKNOWLEDGED: False})

    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "disclaimer")
    assert result["errors"] == {CONF_ACKNOWLEDGED: "must_acknowledge"}
    assert hass.config_entries.async_entries(DOMAIN) == []


async def test_blank_name_is_rejected(hass: HomeAssistant) -> None:
    result = await _to_step(hass, {CONF_CHILD_NAME: "   ", CONF_BIRTH_DATE: "2027-02-14"})
    assert (result["step_id"], result["errors"]) == ("user", {CONF_CHILD_NAME: "name_required"})


async def test_same_child_cannot_be_added_twice(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    config_entry.add_to_hass(hass)
    result = await _to_step(hass, USER_INPUT)
    assert (result["type"], result["reason"]) == (FlowResultType.ABORT, "already_configured")


@pytest.mark.parametrize(
    ("place", "errors"),
    [
        ({CONF_PLACE_NAME: "Crib"}, {"base": "no_sound_source"}),
        ({CONF_PLACE_NAME: "Crib", CONF_FRIGATE_CAMERA: "  "}, {"base": "no_sound_source"}),
        ({CONF_PLACE_NAME: "  ", CONF_FRIGATE_CAMERA: "nursery"}, {CONF_PLACE_NAME: "name_required"}),
    ],
)
async def test_place_needs_a_name_and_a_sound_source(
    hass: HomeAssistant, place: dict[str, Any], errors: dict[str, str]
) -> None:
    result = await _to_step(hass, USER_INPUT, place)
    assert (result["step_id"], result["errors"]) == ("place", errors)


async def test_crying_sensor_is_a_sound_source(hass: HomeAssistant) -> None:
    place = {CONF_PLACE_NAME: "Crib", CONF_CRY_ENTITY: "binary_sensor.camera_cry"}
    result = await _to_step(hass, USER_INPUT, place)
    assert result["step_id"] == "notify"


async def test_alerts_need_somewhere_to_go(hass: HomeAssistant) -> None:
    result = await _to_step(hass, USER_INPUT, PLACE_INPUT, {CONF_NOTIFY_SERVICES: []})
    assert (result["step_id"], result["errors"]) == ("notify", {"base": "no_alert_target"})

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_LOCAL_ALARM: ["siren.bedroom"]})
    assert result["step_id"] == "ai"


async def _options_page(hass: HomeAssistant, entry: MockConfigEntry, page: str) -> Any:
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert (result["type"], result["menu_options"]) == (FlowResultType.MENU, ["notify", "ai", "devices"])
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": page})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, page)
    return result


async def test_options_page_saves_its_own_settings_and_reloads(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    await setup(hass, config_entry)
    first = config_entry.runtime_data.coordinator

    result = await _options_page(hass, config_entry, "notify")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_NOTIFY_SERVICES: [PARENT_A], CONF_LOCAL_ALARM: []}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_NOTIFY_SERVICES] == [PARENT_A]
    assert config_entry.options[CONF_LOCAL_ALARM] == []
    assert config_entry.runtime_data.coordinator is not first


async def test_options_pages_keep_each_others_settings(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    await setup(hass, config_entry)

    result = await _options_page(hass, config_entry, "ai")
    result = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_AI_ENTITIES: ["ai_task.gemini"]})
    assert result["errors"] == {CONF_AI_CONSENT: "ai_consent_required"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_AI_ENTITIES: ["ai_task.gemini"], CONF_AI_CONSENT: True}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY

    result = await _options_page(hass, config_entry, "devices")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SMOKE_ENTITIES: ["binary_sensor.smoke"], CONF_VOX_PLAYER: "media_player.bedroom"}
    )
    await hass.async_block_till_done()

    options = config_entry.options
    assert options[CONF_NOTIFY_SERVICES] == [PARENT_A, "mobile_app_parent_b"]  # untouched by the other pages
    assert (options[CONF_AI_ENTITIES], options[CONF_AI_CONSENT]) == (["ai_task.gemini"], True)
    assert options[CONF_SMOKE_ENTITIES] == ["binary_sensor.smoke"]

    # Clearing a field on one page removes it and leaves the rest alone.
    result = await _options_page(hass, config_entry, "devices")
    result = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_SMOKE_ENTITIES: []})
    await hass.async_block_till_done()
    assert CONF_VOX_PLAYER not in config_entry.options
    assert config_entry.options[CONF_AI_CONSENT] is True


async def test_options_cannot_remove_the_last_alert_target(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    await setup(hass, config_entry)
    result = await _options_page(hass, config_entry, "notify")
    result = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_NOTIFY_SERVICES: []})
    assert result["errors"] == {"base": "no_alert_target"}


async def test_add_and_change_a_sleep_place(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    await setup(hass, config_entry)

    result = await hass.config_entries.subentries.async_init(
        (config_entry.entry_id, SUBENTRY_PLACE), context={"source": SOURCE_USER}
    )
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "user")
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {CONF_PLACE_NAME: "Pram"})
    assert result["errors"] == {"base": "no_sound_source"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_PLACE_NAME: "Pram", CONF_FRIGATE_CAMERA: "living_room"}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    by_title = {place.title: place for place in config_entry.subentries.values()}
    assert set(by_title) == {"Crib", "Pram"}

    pram = by_title["Pram"]
    result = await hass.config_entries.subentries.async_init(
        (config_entry.entry_id, SUBENTRY_PLACE),
        context={"source": SOURCE_RECONFIGURE, "subentry_id": pram.subentry_id},
    )
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "reconfigure")
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {CONF_PLACE_NAME: ""})
    assert result["errors"] == {CONF_PLACE_NAME: "name_required", "base": "no_sound_source"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {CONF_PLACE_NAME: "Stroller", CONF_FRIGATE_CAMERA: "hall", CONF_DOOR_ENTITY: "binary_sensor.door"},
    )
    await hass.async_block_till_done()

    assert (result["type"], result["reason"]) == (FlowResultType.ABORT, "reconfigure_successful")
    changed = config_entry.subentries[pram.subentry_id]
    assert changed.title == "Stroller"
    assert changed.data[CONF_FRIGATE_CAMERA] == "hall"
    assert changed.data[CONF_DOOR_ENTITY] == "binary_sensor.door"
    places = config_entry.runtime_data.coordinator.places
    assert {place.name for place in places.values()} == {"Crib", "Stroller"}
