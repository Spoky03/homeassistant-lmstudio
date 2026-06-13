"""Config flow for LM Studio."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from aiohttp import ClientSession
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_LLM_HASS_API, CONF_PORT, CONF_PROMPT
from homeassistant.core import callback
from homeassistant.helpers import llm
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .api import (
    LMStudioApiError,
    LMStudioAuthError,
    LMStudioClient,
    LMStudioConnectionError,
)
from .const import (
    CONF_API_TOKEN,
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
    DEFAULT_HOST,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_TOKENS,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TEMPERATURE,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
        vol.Optional(CONF_API_TOKEN): str,
    }
)


async def _validate_input(
    session: ClientSession, user_input: dict[str, Any]
) -> dict[str, str]:
    """Validate connection settings."""
    errors: dict[str, str] = {}
    client = LMStudioClient(
        session,
        user_input[CONF_HOST],
        user_input[CONF_PORT],
        user_input.get(CONF_API_TOKEN) or None,
    )
    try:
        await client.async_get_models()
    except LMStudioAuthError:
        errors["base"] = "invalid_auth"
    except LMStudioConnectionError:
        errors["base"] = "cannot_connect"
    except LMStudioApiError:
        errors["base"] = "unknown"
    return errors


async def _async_get_llm_model_options(
    options_flow: OptionsFlow,
) -> list[SelectOptionDict]:
    """Return LLM model options from the configured server."""
    entry = options_flow.config_entry
    client = LMStudioClient(
        async_get_clientsession(options_flow.hass),
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data.get(CONF_API_TOKEN) or None,
    )
    try:
        models = await client.async_get_models()
    except LMStudioApiError:
        return [SelectOptionDict(label="Unable to fetch models", value="")]

    options = [
        SelectOptionDict(
            label=str(model.get("display_name") or model.get("key")),
            value=str(model.get("key")),
        )
        for model in models
        if model.get("type") == "llm" and model.get("key")
    ]
    return options or [SelectOptionDict(label="No LLM models found", value="")]


def _llm_api_selector(options_flow: OptionsFlow) -> SelectSelector:
    """Return selector for Home Assistant LLM APIs."""
    apis = [
        SelectOptionDict(label=api.name, value=api.id)
        for api in llm.async_get_apis(options_flow.hass)
    ]
    return SelectSelector(
        SelectSelectorConfig(options=apis, multiple=True, mode=SelectSelectorMode.DROPDOWN)
    )


async def _options_schema(options_flow: OptionsFlow) -> vol.Schema:
    """Return the options flow schema."""
    model_options = await _async_get_llm_model_options(options_flow)
    options = options_flow.config_entry.options
    current_model = options.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)

    return vol.Schema(
        {
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(
                vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
            ),
            vol.Required(
                CONF_CONTEXT_LENGTH,
                default=options.get(CONF_CONTEXT_LENGTH, DEFAULT_CONTEXT_LENGTH),
            ): vol.All(vol.Coerce(int), vol.Range(min=0)),
            vol.Required(
                CONF_FLASH_ATTENTION,
                default=options.get(CONF_FLASH_ATTENTION, DEFAULT_FLASH_ATTENTION),
            ): bool,
            vol.Optional(
                CONF_CHAT_MODEL,
                description={"suggested_value": current_model},
            ): SelectSelector(
                SelectSelectorConfig(
                    options=model_options,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_PROMPT,
                default=options.get(CONF_PROMPT, ""),
            ): TextSelector(),
            vol.Optional(
                CONF_LLM_HASS_API,
                description={"suggested_value": options.get(CONF_LLM_HASS_API)},
            ): _llm_api_selector(options_flow),
            vol.Required(
                CONF_TEMPERATURE,
                default=options.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE),
            ): vol.All(vol.Coerce(float), vol.Range(min=0, max=2)),
            vol.Required(
                CONF_MAX_TOKENS,
                default=options.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS),
            ): vol.All(vol.Coerce(int), vol.Range(min=0)),
            vol.Required(
                CONF_MAX_HISTORY,
                default=options.get(CONF_MAX_HISTORY, DEFAULT_MAX_HISTORY),
            ): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        }
    )


class LMStudioConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LM Studio."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return LMStudioOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_API_TOKEN):
                user_input[CONF_API_TOKEN] = None
            errors = await _validate_input(
                async_get_clientsession(self.hass), user_input
            )
            if not errors:
                host = user_input[CONF_HOST]
                port = user_input[CONF_PORT]
                await self.async_set_unique_id(f"{host}:{port}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"LM Studio ({host}:{port})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauthentication."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            data = {**reauth_entry.data, **user_input}
            errors = await _validate_input(async_get_clientsession(self.hass), data)
            if not errors:
                self.hass.config_entries.async_update_entry(reauth_entry, data=data)
                await self.hass.config_entries.async_reload(reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Optional(CONF_API_TOKEN): str}),
            errors=errors,
        )


class LMStudioOptionsFlowHandler(OptionsFlow):
    """Handle LM Studio options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage integration options."""
        if user_input is not None:
            if not user_input.get(CONF_PROMPT):
                user_input[CONF_PROMPT] = None
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=await _options_schema(self),
        )
