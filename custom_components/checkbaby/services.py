"""Actions of the CheckBaby integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, SNOOZE_SECONDS
from .coordinator import CheckBabyCoordinator
from .schema_compat import vol
from .types import AlertLevel, ChildState

ATTR_ENTRY = "config_entry_id"
ATTR_MINUTES = "minutes"
ATTR_LEVEL = "level"
ATTR_WITH_AI = "with_ai"
ATTR_NOTIFY = "notify"

_BASE = {vol.Optional(ATTR_ENTRY): cv.string}


def _schema(extra: dict[Any, Any] | None = None) -> Any:
    return vol.Schema({**_BASE, **(extra or {})})


def _coordinator(call: ServiceCall) -> CheckBabyCoordinator:
    """Find the child an action is for; unambiguous if only one is set up."""
    entries = [
        entry
        for entry in call.hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]
    entry_id = call.data.get(ATTR_ENTRY)
    if entry_id is not None:
        entries = [entry for entry in entries if entry.entry_id == entry_id]
    if len(entries) != 1:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="entry_required")
    coordinator: CheckBabyCoordinator = entries[0].runtime_data.coordinator
    return coordinator


async def _acknowledge(call: ServiceCall) -> None:
    _coordinator(call).acknowledge()


async def _snooze(call: ServiceCall) -> None:
    _coordinator(call).snooze(float(call.data[ATTR_MINUTES]) * 60.0)


async def _test_alert(call: ServiceCall) -> None:
    _coordinator(call).test_alert(AlertLevel[str(call.data[ATTR_LEVEL]).upper()])


async def _start_sleep(call: ServiceCall) -> None:
    _coordinator(call).force_state(ChildState.ASLEEP)


async def _end_sleep(call: ServiceCall) -> None:
    _coordinator(call).force_state(ChildState.AWAKE)


async def _assess_now(call: ServiceCall) -> ServiceResponse:
    assessment = await _coordinator(call).async_assess("manual", manual=True)
    if assessment is None:
        return {"assessment": None}
    data = asdict(assessment)
    data["hazards"] = list(assessment.hazards)
    return {"assessment": data}


async def _quick_check(call: ServiceCall) -> ServiceResponse:
    coordinator = _coordinator(call)
    if call.data[ATTR_WITH_AI]:
        await coordinator.async_assess("manual", manual=True)
    result = coordinator.quick_check()
    if call.data[ATTR_NOTIFY]:
        await coordinator.notifier.async_send_text(result["summary"], level=AlertLevel.INFO)
    return result


async def _night_report(call: ServiceCall) -> ServiceResponse:
    coordinator = _coordinator(call)
    result = coordinator.night_report()
    if call.data[ATTR_NOTIFY]:
        await coordinator.notifier.async_send_text(result["summary"], level=AlertLevel.INFO)
    return result


@callback
def async_register_services(hass: HomeAssistant) -> None:
    """Register all actions."""
    minutes = vol.All(vol.Coerce(float), vol.Range(min=1, max=120))
    register = hass.services.async_register
    register(DOMAIN, "acknowledge", _acknowledge, schema=_schema())
    register(
        DOMAIN,
        "snooze",
        _snooze,
        schema=_schema({vol.Optional(ATTR_MINUTES, default=SNOOZE_SECONDS / 60): minutes}),
    )
    register(
        DOMAIN,
        "test_alert",
        _test_alert,
        schema=_schema({vol.Optional(ATTR_LEVEL, default="critical"): vol.In(["warning", "critical"])}),
    )
    register(DOMAIN, "start_sleep", _start_sleep, schema=_schema())
    register(DOMAIN, "end_sleep", _end_sleep, schema=_schema())
    register(DOMAIN, "assess_now", _assess_now, schema=_schema(), supports_response=SupportsResponse.OPTIONAL)
    register(
        DOMAIN,
        "quick_check",
        _quick_check,
        schema=_schema(
            {
                vol.Optional(ATTR_WITH_AI, default=False): cv.boolean,
                vol.Optional(ATTR_NOTIFY, default=False): cv.boolean,
            }
        ),
        supports_response=SupportsResponse.OPTIONAL,
    )
    register(
        DOMAIN,
        "night_report",
        _night_report,
        schema=_schema({vol.Optional(ATTR_NOTIFY, default=False): cv.boolean}),
        supports_response=SupportsResponse.OPTIONAL,
    )
