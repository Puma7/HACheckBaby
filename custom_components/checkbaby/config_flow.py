"""Config flow for CheckBaby."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import BooleanSelector, DateSelector, TextSelector
from homeassistant.util import slugify

from .const import CONF_ACKNOWLEDGED, CONF_BIRTH_DATE, CONF_CHILD_NAME, DOMAIN

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CHILD_NAME): TextSelector(),
        vol.Required(CONF_BIRTH_DATE): DateSelector(),
    }
)
DISCLAIMER_SCHEMA = vol.Schema({vol.Required(CONF_ACKNOWLEDGED, default=False): BooleanSelector()})


class CheckBabyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up one child: name and birth date, then the intended-use notice."""

    VERSION = 1

    def __init__(self) -> None:
        """Start with nothing collected."""
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the child's name and birth date (or expected due date)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            name = str(user_input[CONF_CHILD_NAME]).strip()
            if not name:
                errors[CONF_CHILD_NAME] = "name_required"
            else:
                await self.async_set_unique_id(slugify(name))
                self._abort_if_unique_id_configured()
                self._data = {
                    CONF_CHILD_NAME: name,
                    CONF_BIRTH_DATE: user_input[CONF_BIRTH_DATE],
                }
                return await self.async_step_disclaimer()

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_disclaimer(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show the intended-use notice; the entry exists only once it is confirmed."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input.get(CONF_ACKNOWLEDGED) is True:
                return self.async_create_entry(title=self._data[CONF_CHILD_NAME], data=self._data)
            errors[CONF_ACKNOWLEDGED] = "must_acknowledge"

        return self.async_show_form(step_id="disclaimer", data_schema=DISCLAIMER_SCHEMA, errors=errors)
