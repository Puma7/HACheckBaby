"""Shared fixtures."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.checkbaby.const import CONF_BIRTH_DATE, CONF_CHILD_NAME, DOMAIN


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations: None) -> Generator[None]:
    """Let Home Assistant load the integration from custom_components."""
    yield


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """A child with a fixed birth date."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Testkind",
        unique_id="testkind",
        data={CONF_CHILD_NAME: "Testkind", CONF_BIRTH_DATE: "2027-02-14"},
    )
