"""Shared chat handling for LM Studio conversation and AI task entities."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator, Callable
from typing import Any

import voluptuous as vol
from voluptuous_openapi import convert

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm
from homeassistant.util.json import json_loads

from .api import LMStudioApiError, LMStudioClient
from .const import DOMAIN, MAX_TOOL_ITERATIONS
from .helpers import (
    get_chat_max_history,
    get_chat_max_tokens,
    get_chat_model,
    get_chat_temperature,
)

_LOGGER = logging.getLogger(__name__)


def _format_tool(
    tool: llm.Tool, custom_serializer: Callable[[Any], Any] | None
) -> dict[str, Any]:
    """Format a Home Assistant tool for OpenAI-compatible APIs."""
    schema = convert(tool.parameters, custom_serializer=custom_serializer)
    tool_spec: dict[str, Any] = {
        "type": "function",
        "function": {
            "name": tool.name,
            "parameters": schema,
        },
    }
    if tool.description:
        tool_spec["function"]["description"] = tool.description
    return tool_spec


def _parse_tool_arguments(arguments: str | dict[str, Any] | None) -> dict[str, Any]:
    """Parse tool arguments from the LM Studio response."""
    if arguments is None:
        return {}
    if isinstance(arguments, dict):
        return arguments
    if not arguments:
        return {}
    try:
        parsed = json_loads(arguments)
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _convert_content(
    chat_content: conversation.Content,
) -> dict[str, Any]:
    """Convert chat log content to OpenAI message format."""
    if isinstance(chat_content, conversation.ToolResultContent):
        return {
            "role": "tool",
            "tool_call_id": chat_content.tool_call_id,
            "content": json.dumps(chat_content.tool_result),
        }
    if isinstance(chat_content, conversation.AssistantContent):
        message: dict[str, Any] = {
            "role": "assistant",
            "content": chat_content.content,
        }
        if chat_content.tool_calls:
            message["tool_calls"] = [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.tool_name,
                        "arguments": json.dumps(tool_call.tool_args),
                    },
                }
                for tool_call in chat_content.tool_calls
            ]
        return message
    if isinstance(chat_content, conversation.UserContent):
        return {"role": "user", "content": chat_content.content or ""}
    if isinstance(chat_content, conversation.SystemContent):
        return {"role": "system", "content": chat_content.content or ""}
    raise TypeError(f"Unexpected content type: {type(chat_content)}")


def _trim_messages(messages: list[dict[str, Any]], max_history: int) -> None:
    """Trim message history while keeping the system prompt."""
    if max_history < 1 or len(messages) <= 1:
        return

    system_messages = [
        message for message in messages if message.get("role") == "system"
    ]
    other_messages = [
        message for message in messages if message.get("role") != "system"
    ]
    if len(other_messages) <= max_history * 2:
        return

    messages[:] = [
        *system_messages,
        *other_messages[-(max_history * 2) :],
    ]


async def _message_to_delta(
    message: dict[str, Any],
) -> AsyncGenerator[conversation.AssistantContentDeltaDict]:
    """Convert a chat completion message to HA delta format."""
    delta: conversation.AssistantContentDeltaDict = {"role": "assistant"}
    if content := message.get("content"):
        delta["content"] = content
    if tool_calls := message.get("tool_calls"):
        delta["tool_calls"] = [
            llm.ToolInput(
                tool_name=tool_call["function"]["name"],
                tool_args=_parse_tool_arguments(tool_call["function"].get("arguments")),
                id=tool_call.get("id") or tool_call["function"]["name"],
            )
            for tool_call in tool_calls
        ]
    yield delta


class LMStudioChatHandler:
    """Handle chat log processing against LM Studio."""

    def __init__(self, client: LMStudioClient, entry: ConfigEntry) -> None:
        """Initialize."""
        self.client = client
        self.entry = entry

    async def async_handle_chat_log(
        self,
        chat_log: conversation.ChatLog,
        entity_id: str,
        *,
        structure: vol.Schema | None = None,
    ) -> None:
        """Generate a response for the chat log."""
        model = get_chat_model(self.entry)
        if not model:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="chat_model_not_configured",
            )

        messages = [_convert_content(content) for content in chat_log.content]
        _trim_messages(messages, get_chat_max_history(self.entry))

        tools: list[dict[str, Any]] | None = None
        response_format: dict[str, Any] | None = None
        if chat_log.llm_api:
            tools = [
                _format_tool(tool, chat_log.llm_api.custom_serializer)
                for tool in chat_log.llm_api.tools
            ]
        if structure is not None:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_response",
                    "schema": convert(
                        structure,
                        custom_serializer=(
                            chat_log.llm_api.custom_serializer
                            if chat_log.llm_api
                            else llm.selector_serializer
                        ),
                    ),
                },
            }

        for _iteration in range(MAX_TOOL_ITERATIONS):
            try:
                response = await self.client.async_chat_completion(
                    messages,
                    model,
                    tools=tools,
                    temperature=get_chat_temperature(self.entry),
                    max_tokens=get_chat_max_tokens(self.entry),
                    response_format=response_format,
                )
            except LMStudioApiError as err:
                _LOGGER.error("Error talking to LM Studio: %s", err)
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="chat_error",
                    translation_placeholders={"error": str(err)},
                ) from err

            choices = response.get("choices") or []
            if not choices:
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="chat_empty_response",
                )

            message = choices[0].get("message") or {}
            messages.extend(
                [
                    _convert_content(content)
                    async for content in chat_log.async_add_delta_content_stream(
                        entity_id,
                        _message_to_delta(message),
                    )
                ]
            )

            if not chat_log.unresponded_tool_results:
                break
