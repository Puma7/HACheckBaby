"""A speaker that stands in for the one in the parents' bedroom."""

from __future__ import annotations

from typing import Any

from homeassistant.components.media_player import MediaPlayerEntity, MediaPlayerEntityFeature, MediaPlayerState
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import LabEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the speaker."""
    async_add_entities([LabSpeaker(hass, "speaker", "Speaker")])


class LabSpeaker(LabEntity, MediaPlayerEntity):
    """Records what it was asked to play."""

    _attr_supported_features = MediaPlayerEntityFeature.PLAY_MEDIA | MediaPlayerEntityFeature.STOP
    _attr_state = MediaPlayerState.IDLE

    async def async_play_media(self, media_type: str, media_id: str, **kwargs: Any) -> None:
        """Play the child's room audio."""
        self._attr_state = MediaPlayerState.PLAYING
        self.lab.media.append({"action": "play", "media_id": media_id, "media_type": media_type})
        self.lab.changed()

    async def async_media_stop(self) -> None:
        """Stop."""
        self._attr_state = MediaPlayerState.IDLE
        self.lab.media.append({"action": "stop"})
        self.lab.changed()
