"""Conversation platform for LM Studio."""

from __future__ import annotations

from typing import Literal

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .chat import LMStudioChatHandler
from .const import DOMAIN
from .entity import LMStudioHubEntity
from .helpers import get_chat_llm_hass_api, get_chat_prompt
from .runtime import LMStudioRuntimeData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LM Studio conversation agent."""
    runtime: LMStudioRuntimeData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LMStudioConversationEntity(entry, runtime)])


class LMStudioConversationEntity(
    conversation.ConversationEntity,
    conversation.AbstractConversationAgent,
    LMStudioHubEntity,
):
    """LM Studio conversation agent."""

    _attr_translation_key = "conversation"

    def __init__(self, entry: ConfigEntry, runtime: LMStudioRuntimeData) -> None:
        """Initialize the agent."""
        super().__init__(entry, runtime)
        self._attr_unique_id = f"{entry.entry_id}_conversation"
        self._chat_handler = LMStudioChatHandler(runtime.models.client, entry)
        if get_chat_llm_hass_api(entry):
            self._attr_supported_features = (
                conversation.ConversationEntityFeature.CONTROL
            )

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return supported languages."""
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        """Register the conversation agent."""
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self.entry, self)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister the conversation agent."""
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        """Process a conversation message."""
        try:
            await chat_log.async_provide_llm_data(
                user_input.as_llm_context(DOMAIN),
                get_chat_llm_hass_api(self.entry),
                get_chat_prompt(self.entry),
                user_input.extra_system_prompt,
            )
        except conversation.ConverseError as err:
            return err.as_conversation_result()

        await self._chat_handler.async_handle_chat_log(
            chat_log,
            self.entity_id,
        )

        return conversation.async_get_result_from_chat_log(user_input, chat_log)
