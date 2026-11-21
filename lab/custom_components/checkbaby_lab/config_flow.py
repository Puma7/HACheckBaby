"""Config flow of the lab simulator: one entry, no questions."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class LabConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create the single lab entry."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Add the lab from the user interface."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="CheckBaby Lab", data={})

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Add the lab from configuration.yaml."""
        return await self.async_step_user()
