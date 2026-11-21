"""Config flow."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.checkbaby.const import (
    CONF_ACKNOWLEDGED,
    CONF_BIRTH_DATE,
    CONF_CHILD_NAME,
    DOMAIN,
)

USER_INPUT = {CONF_CHILD_NAME: "  Testkind ", CONF_BIRTH_DATE: "2027-02-14"}


async def test_flow_creates_entry_after_acknowledgement(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "disclaimer"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_ACKNOWLEDGED: True})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Testkind"
    assert result["data"] == {CONF_CHILD_NAME: "Testkind", CONF_BIRTH_DATE: "2027-02-14"}
    assert result["result"].unique_id == "testkind"


async def test_no_entry_without_acknowledgement(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_ACKNOWLEDGED: False})

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "disclaimer"
    assert result["errors"] == {CONF_ACKNOWLEDGED: "must_acknowledge"}
    assert hass.config_entries.async_entries(DOMAIN) == []


async def test_blank_name_is_rejected(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CHILD_NAME: "   ", CONF_BIRTH_DATE: "2027-02-14"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {CONF_CHILD_NAME: "name_required"}


async def test_same_child_cannot_be_added_twice(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
