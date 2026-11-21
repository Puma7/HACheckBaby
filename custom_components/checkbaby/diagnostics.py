"""Diagnostics for CheckBaby."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import CONF_AUDIO_URL, CONF_BIRTH_DATE, CONF_CHILD_NAME
from .models import CheckBabyConfigEntry

TO_REDACT = {CONF_CHILD_NAME, CONF_BIRTH_DATE, CONF_AUDIO_URL, "audio_url", "name", "title", "reason"}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: CheckBabyConfigEntry) -> dict[str, Any]:
    """Return what helps to understand a decision, without the child's details."""
    coordinator = entry.runtime_data.coordinator
    monitor = coordinator.monitor
    snapshot = asdict(coordinator.data)
    snapshot["state"] = coordinator.data.state.value
    snapshot["level"] = coordinator.data.level.name.lower()
    snapshot["alert_kind"] = coordinator.data.alert_kind.value if coordinator.data.alert_kind else None
    payload = {
        "entry": dict(entry.data),
        "options": dict(entry.options),
        "places": [asdict(place) for place in coordinator.places.values()],
        "settings": coordinator.settings.to_dict(),
        "profile": coordinator.profile.value,
        "snapshot": snapshot,
        "problems": list(monitor.problems),
        "events": list(monitor.events),
        "ai_calls_last_hour": coordinator.budget.used(dt_util.utcnow().timestamp()),
    }
    redacted: dict[str, Any] = async_redact_data(payload, TO_REDACT)
    return redacted
