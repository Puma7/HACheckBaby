"""CheckBaby: a smart baby monitor built on Frigate."""

from __future__ import annotations

from datetime import date

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import config_validation as cv, issue_registry as ir
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .const import CONF_BIRTH_DATE, CONF_CHILD_NAME, DOMAIN, PLATFORMS
from .coordinator import CheckBabyCoordinator
from .models import CheckBabyConfigEntry, CheckBabyData
from .services import async_register_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the actions once, independent of any entry."""
    async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: CheckBabyConfigEntry) -> bool:
    """Set up one child."""
    raw_birth_date = entry.data[CONF_BIRTH_DATE]
    try:
        birth_date = date.fromisoformat(raw_birth_date)
    except (TypeError, ValueError) as err:
        raise ConfigEntryError(f"Invalid birth date: {raw_birth_date!r}") from err

    child_name = entry.data[CONF_CHILD_NAME]
    coordinator = CheckBabyCoordinator(hass, entry, child_name, birth_date)
    entry.runtime_data = CheckBabyData(child_name=child_name, birth_date=birth_date, coordinator=coordinator)
    await coordinator.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Options and sleep places are read at start, so any change restarts the entry.
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: CheckBabyConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: CheckBabyConfigEntry) -> bool:
    """Unload one child."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.coordinator.async_stop()
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: CheckBabyConfigEntry) -> None:
    """Delete what the entry stored."""
    await Store[dict[str, object]](hass, 1, f"{DOMAIN}.{entry.entry_id}").async_remove()
    for key in ("no_alert_target", "no_sleep_place", "mqtt_missing"):
        ir.async_delete_issue(hass, DOMAIN, f"{key}_{entry.entry_id}")
