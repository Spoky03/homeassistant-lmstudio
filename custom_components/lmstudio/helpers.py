"""Helpers for the LM Studio integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LLM_HASS_API, CONF_PROMPT, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    ATTR_USES_DEFAULT,
    CONF_CHAT_MODEL,
    CONF_CONTEXT_LENGTH,
    CONF_FLASH_ATTENTION,
    CONF_MAX_HISTORY,
    CONF_MAX_TOKENS,
    CONF_SCAN_INTERVAL,
    CONF_TEMPERATURE,
    DEFAULT_CHAT_MODEL,
    DEFAULT_CONTEXT_LENGTH,
    DEFAULT_FLASH_ATTENTION,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_TOKENS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TEMPERATURE,
    DOMAIN,
    UNIQUE_ID_CONTEXT_LENGTH_SUFFIX,
    UNIQUE_ID_FLASH_ATTENTION_SUFFIX,
)


def get_chat_model(entry: ConfigEntry) -> str | None:
    """Return configured chat model key."""
    model = entry.options.get(CONF_CHAT_MODEL) or DEFAULT_CHAT_MODEL
    return model or None


def get_chat_temperature(entry: ConfigEntry) -> float:
    """Return configured chat temperature."""
    return float(entry.options.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE))


def get_chat_max_tokens(entry: ConfigEntry) -> int | None:
    """Return configured max tokens, or None for server default."""
    max_tokens = int(entry.options.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS))
    return max_tokens if max_tokens > 0 else None


def get_chat_max_history(entry: ConfigEntry) -> int:
    """Return configured chat history size."""
    return int(entry.options.get(CONF_MAX_HISTORY, DEFAULT_MAX_HISTORY))


def get_chat_prompt(entry: ConfigEntry) -> str | None:
    """Return optional custom prompt."""
    prompt = entry.options.get(CONF_PROMPT)
    return prompt if prompt else None


def get_chat_llm_hass_api(entry: ConfigEntry):
    """Return selected Home Assistant LLM APIs."""
    return entry.options.get(CONF_LLM_HASS_API)


def get_scan_interval(entry: ConfigEntry) -> int:
    """Return the configured poll interval in seconds."""
    return int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))


def get_load_context_length(entry: ConfigEntry) -> int | None:
    """Return configured context length, or None to use the model default."""
    context_length = int(
        entry.options.get(CONF_CONTEXT_LENGTH, DEFAULT_CONTEXT_LENGTH)
    )
    return context_length if context_length > 0 else None


def get_load_flash_attention(entry: ConfigEntry) -> bool:
    """Return whether flash attention should be requested when loading."""
    return bool(entry.options.get(CONF_FLASH_ATTENTION, DEFAULT_FLASH_ATTENTION))


def _model_option_unique_id(entry_id: str, model_key: str, suffix: str) -> str:
    """Return the entity unique id for a per-model option entity."""
    return f"{entry_id}_{model_key}_{suffix}"


def _read_entity_state(hass: HomeAssistant, domain: str, unique_id: str) -> str | None:
    """Return the state string for an entity unique id."""
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(domain, DOMAIN, unique_id)
    if not entity_id or (state := hass.states.get(entity_id)) is None:
        return None
    if state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
        return None
    return state.state


def resolve_model_load_context_length(
    hass: HomeAssistant, entry: ConfigEntry, model_key: str
) -> int | None:
    """Return effective context length for loading a model."""
    unique_id = _model_option_unique_id(
        entry.entry_id, model_key, UNIQUE_ID_CONTEXT_LENGTH_SUFFIX
    )
    state = _read_entity_state(hass, "number", unique_id)
    if state is not None:
        try:
            value = int(float(state))
        except (TypeError, ValueError):
            value = 0
        if value > 0:
            return value
    return get_load_context_length(entry)


def resolve_model_load_flash_attention(
    hass: HomeAssistant, entry: ConfigEntry, model_key: str
) -> bool | None:
    """Return effective flash attention setting for loading a model."""
    unique_id = _model_option_unique_id(
        entry.entry_id, model_key, UNIQUE_ID_FLASH_ATTENTION_SUFFIX
    )
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("switch", DOMAIN, unique_id)
    if entity_id and (state := hass.states.get(entity_id)) is not None:
        if state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            if state.attributes.get(ATTR_USES_DEFAULT, True):
                pass
            else:
                return state.state == "on"
    if get_load_flash_attention(entry):
        return True
    return None
