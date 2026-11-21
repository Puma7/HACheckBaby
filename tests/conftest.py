"""Shared fixtures."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.checkbaby.const import (
    CONF_BIRTH_DATE,
    CONF_CAMERA_ENTITY,
    CONF_CHILD_NAME,
    CONF_FRIGATE_CAMERA,
    CONF_LOCAL_ALARM,
    CONF_NOTIFY_SERVICES,
    DOMAIN,
    SUBENTRY_PLACE,
)

PARENT_A = "mobile_app_parent_a"
PARENT_B = "mobile_app_parent_b"
CAMERA = "nursery"
SIREN = "siren.bedroom"


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations: None) -> Generator[None]:
    """Let Home Assistant load the integration from custom_components."""
    yield


def make_entry(
    *,
    place: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
    birth_date: str = "2027-02-14",
    places: list[tuple[str, dict[str, Any]]] | None = None,
) -> MockConfigEntry:
    """A child with one sleep place on a Frigate camera and two parents' phones."""
    if places is None:
        default_place = {CONF_FRIGATE_CAMERA: CAMERA, CONF_CAMERA_ENTITY: "camera.nursery"}
        places = [("Crib", default_place if place is None else place)]
    default_options = {CONF_NOTIFY_SERVICES: [PARENT_A, PARENT_B], CONF_LOCAL_ALARM: [SIREN]}
    return MockConfigEntry(
        domain=DOMAIN,
        title="Testkind",
        unique_id="testkind",
        data={CONF_CHILD_NAME: "Testkind", CONF_BIRTH_DATE: birth_date},
        options=default_options if options is None else options,
        subentries_data=[
            ConfigSubentryData(data=data, subentry_type=SUBENTRY_PLACE, title=title, unique_id=None)
            for title, data in places
        ],
    )


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """The default child."""
    return make_entry()


@pytest.fixture
def pushes(hass: HomeAssistant) -> dict[str, list[ServiceCall]]:
    """Calls to the parents' notify services."""
    return {name: async_mock_service(hass, "notify", name) for name in (PARENT_A, PARENT_B)}


@pytest.fixture
def local_alarm(hass: HomeAssistant) -> dict[str, list[ServiceCall]]:
    """Calls that switch the local alarm channel."""
    return {
        "on": async_mock_service(hass, "homeassistant", "turn_on"),
        "off": async_mock_service(hass, "homeassistant", "turn_off"),
    }


def notices(hass: HomeAssistant) -> dict[str, str]:
    """Home Assistant's own notifications: the part of the id after the entry, and the message."""
    from homeassistant.components.persistent_notification import _async_get_or_create_notifications  # noqa: PLC0415

    return {
        key.split("_", 2)[2]: note["message"]
        for key, note in _async_get_or_create_notifications(hass).items()
        if key.startswith("checkbaby_")
    }


async def setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Add and set up an entry; the camera and the siren it refers to exist."""
    hass.states.async_set("camera.nursery", "idle")
    hass.states.async_set(SIREN, "off")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def advance(hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: float, step: float = 2.0) -> None:
    """Let time pass so that the monitor ticks."""
    remaining = seconds
    while remaining > 0:
        delta = min(step, remaining)
        freezer.tick(delta)
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done()
        remaining -= delta


def entity_id(hass: HomeAssistant, entry: MockConfigEntry, platform: str, key: str) -> str:
    """Look an entity up by its key."""
    found = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{entry.entry_id}_{key}")
    assert found is not None, f"{platform}.{key} not registered"
    return found


def state_of(hass: HomeAssistant, entry: MockConfigEntry, platform: str, key: str) -> str:
    """The state of an entity, by key."""
    state = hass.states.get(entity_id(hass, entry, platform, key))
    assert state is not None
    return state.state


async def turn_on(hass: HomeAssistant, entry: MockConfigEntry, key: str) -> None:
    """Switch a setting on."""
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id(hass, entry, "switch", key)}, blocking=True
    )
    await hass.async_block_till_done()
