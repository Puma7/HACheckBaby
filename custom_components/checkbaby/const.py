"""Constants for the CheckBaby integration."""

from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "checkbaby"

CONF_CHILD_NAME: Final = "child_name"
CONF_BIRTH_DATE: Final = "birth_date"
CONF_ACKNOWLEDGED: Final = "acknowledged"

PLATFORMS: Final[list[Platform]] = [Platform.SENSOR]
