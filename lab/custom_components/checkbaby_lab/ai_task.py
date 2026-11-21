"""An AI task that answers from a script instead of a model.

The call still goes through Home Assistant's real ai_task action, with its
schema validation and its resolving of the camera attachment. Only the model
behind it is replaced.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from homeassistant.components import ai_task, conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .entity import LabEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the scripted AI task."""
    async_add_entities([LabAITask(hass, "ai", "AI")])


class LabAITask(LabEntity, ai_task.AITaskEntity):
    """Records what it was asked and returns the scripted answer."""

    _attr_supported_features = (
        ai_task.AITaskEntityFeature.GENERATE_DATA | ai_task.AITaskEntityFeature.SUPPORT_ATTACHMENTS
    )

    async def _async_generate_data(
        self, task: ai_task.GenDataTask, chat_log: conversation.ChatLog
    ) -> ai_task.GenDataTaskResult:
        attachments = []
        for attachment in task.attachments or []:
            path = Path(attachment.path)
            exists = await self.hass.async_add_executor_job(path.is_file)
            size = (await self.hass.async_add_executor_job(path.stat)).st_size if exists else 0
            attachments.append(
                {"media_content_id": attachment.media_content_id, "mime_type": attachment.mime_type, "bytes": size}
            )
        self.lab.ai_calls.append(
            {
                "at": dt_util.utcnow().timestamp(),
                "name": task.name,
                "instructions": task.instructions,
                "has_structure": task.structure is not None,
                "attachments": attachments,
            }
        )
        self.lab.changed()
        answer = self.lab.ai_answer
        if answer == "error":
            raise HomeAssistantError("Lab: the model is unavailable")
        if answer == "slow":
            await asyncio.sleep(60)
            answer = {}
        return ai_task.GenDataTaskResult(conversation_id=chat_log.conversation_id, data=answer)
