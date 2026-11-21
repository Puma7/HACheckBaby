"""CheckBaby: a smart baby monitor built on Frigate."""

from __future__ import annotations

from datetime import date

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError

from .const import CONF_BIRTH_DATE, CONF_CHILD_NAME, PLATFORMS
from .models import CheckBabyConfigEntry, CheckBabyData


async def async_setup_entry(hass: HomeAssistant, entry: CheckBabyConfigEntry) -> bool:
    """Set up one child."""
    raw_birth_date = entry.data[CONF_BIRTH_DATE]
    try:
        birth_date = date.fromisoformat(raw_birth_date)
    except (TypeError, ValueError) as err:
        raise ConfigEntryError(f"Invalid birth date: {raw_birth_date!r}") from err

    entry.runtime_data = CheckBabyData(
        child_name=entry.data[CONF_CHILD_NAME],
        birth_date=birth_date,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CheckBabyConfigEntry) -> bool:
    """Unload one child."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
