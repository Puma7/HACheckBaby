"""Setup, unload and the age profile sensor."""

from __future__ import annotations

from datetime import timedelta

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.checkbaby.const import CONF_BIRTH_DATE, CONF_CHILD_NAME, DOMAIN


def _profile_entity_id(hass: HomeAssistant, entry: MockConfigEntry) -> str:
    entity_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_age_profile")
    assert entity_id is not None
    return entity_id


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        ("2027-01-10 12:00:00", "newborn"),  # before the birth
        ("2027-03-01 12:00:00", "newborn"),
        ("2027-06-01 12:00:00", "infant"),
        ("2028-03-01 12:00:00", "toddler"),
    ],
)
async def test_age_profile_follows_the_date(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    today: str,
    expected: str,
) -> None:
    freezer.move_to(today)
    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(_profile_entity_id(hass, config_entry))
    assert state is not None
    assert state.state == expected


async def test_age_profile_changes_at_midnight(
    hass: HomeAssistant, config_entry: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    await hass.config.async_set_time_zone("UTC")
    # Born 2027-02-14; day 91 is 2027-05-16.
    freezer.move_to("2027-05-15 23:59:00+00:00")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    entity_id = _profile_entity_id(hass, config_entry)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "newborn"

    freezer.move_to("2027-05-16 00:00:10+00:00")
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=1))
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "infant"


async def test_unload_removes_the_sensor(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    entity_id = _profile_entity_id(hass, config_entry)

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.NOT_LOADED
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unavailable"


async def test_invalid_birth_date_fails_setup(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Testkind",
        data={CONF_CHILD_NAME: "Testkind", CONF_BIRTH_DATE: "not-a-date"},
    )
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR
