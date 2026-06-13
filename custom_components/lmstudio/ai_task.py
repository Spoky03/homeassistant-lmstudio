"""AI Task platform for LM Studio."""

from __future__ import annotations

from json import JSONDecodeError
import logging

from homeassistant.components import ai_task, conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.json import json_loads

from .chat import LMStudioChatHandler
from .const import DOMAIN
from .entity import LMStudioHubEntity
from .runtime import LMStudioRuntimeData

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LM Studio AI task entity."""
    runtime: LMStudioRuntimeData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LMStudioAITaskEntity(entry, runtime)])


class LMStudioAITaskEntity(ai_task.AITaskEntity, LMStudioHubEntity):
    """LM Studio AI task entity."""

    _attr_translation_key = "ai_task"
    _attr_supported_features = ai_task.AITaskEntityFeature.GENERATE_DATA

    def __init__(self, entry: ConfigEntry, runtime: LMStudioRuntimeData) -> None:
        """Initialize the AI task entity."""
        super().__init__(entry, runtime)
        self._attr_unique_id = f"{entry.entry_id}_ai_task"
        self._chat_handler = LMStudioChatHandler(runtime.models.client, entry)

    async def _async_generate_data(
        self,
        task: ai_task.GenDataTask,
        chat_log: conversation.ChatLog,
    ) -> ai_task.GenDataTaskResult:
        """Handle a generate-data task."""
        await self._chat_handler.async_handle_chat_log(
            chat_log,
            self.entity_id,
            structure=task.structure,
        )

        if not isinstance(chat_log.content[-1], conversation.AssistantContent):
            raise HomeAssistantError("Last content in chat log is not assistant content")

        text = chat_log.content[-1].content or ""
        if not task.structure:
            return ai_task.GenDataTaskResult(
                conversation_id=chat_log.conversation_id,
                data=text,
            )

        try:
            data = json_loads(text)
        except JSONDecodeError as err:
            _LOGGER.error(
                "Failed to parse structured LM Studio response: %s. Response: %s",
                err,
                text,
            )
            raise HomeAssistantError(
                "LM Studio returned invalid structured data"
            ) from err

        return ai_task.GenDataTaskResult(
            conversation_id=chat_log.conversation_id,
            data=data,
        )
