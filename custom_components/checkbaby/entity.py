"""Base entity for CheckBaby."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CheckBabyCoordinator
from .monitor import Snapshot


class CheckBabyEntity(CoordinatorEntity[CheckBabyCoordinator]):
    """An entity of one child."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CheckBabyCoordinator, key: str) -> None:
        """Name and attach the entity to the child's device."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=coordinator.child_name,
            manufacturer="CheckBaby",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def snapshot(self) -> Snapshot:
        """The latest monitor snapshot."""
        return self.coordinator.data
