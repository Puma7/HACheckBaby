"""Buttons for CheckBaby."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import SNOOZE_SECONDS
from .coordinator import CheckBabyCoordinator
from .entity import CheckBabyEntity
from .models import CheckBabyConfigEntry


async def _acknowledge(coordinator: CheckBabyCoordinator) -> None:
    coordinator.acknowledge()


async def _snooze(coordinator: CheckBabyCoordinator) -> None:
    coordinator.snooze(SNOOZE_SECONDS)


async def _test_alert(coordinator: CheckBabyCoordinator) -> None:
    coordinator.test_alert()


async def _assess(coordinator: CheckBabyCoordinator) -> None:
    await coordinator.async_assess_and_tell()


async def _quick_check(coordinator: CheckBabyCoordinator) -> None:
    await coordinator.notifier.async_send_text(coordinator.quick_check()["summary"], topic="quick_check")


async def _night_report(coordinator: CheckBabyCoordinator) -> None:
    await coordinator.notifier.async_send_text(coordinator.night_report()["summary"], topic="night_report")


BUTTONS: tuple[tuple[str, Callable[[CheckBabyCoordinator], Awaitable[None]], EntityCategory | None], ...] = (
    ("acknowledge", _acknowledge, None),
    ("snooze", _snooze, None),
    ("quick_check", _quick_check, None),
    ("assess_now", _assess, None),
    ("night_report", _night_report, None),
    ("test_alert", _test_alert, EntityCategory.DIAGNOSTIC),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CheckBabyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the buttons of one child."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(CheckBabyButton(coordinator, *button) for button in BUTTONS)


class CheckBabyButton(CheckBabyEntity, ButtonEntity):
    """Runs one action."""

    def __init__(
        self,
        coordinator: CheckBabyCoordinator,
        key: str,
        action: Callable[[CheckBabyCoordinator], Awaitable[None]],
        category: EntityCategory | None,
    ) -> None:
        """Bind the button to its action."""
        super().__init__(coordinator, key)
        self._action = action
        self._attr_entity_category = category

    async def async_press(self) -> None:
        """Run the action."""
        await self._action(self.coordinator)
