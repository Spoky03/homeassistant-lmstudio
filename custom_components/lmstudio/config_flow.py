"""Config flow for LM Studio."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from aiohttp import ClientSession
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    LMStudioApiError,
    LMStudioAuthError,
    LMStudioClient,
    LMStudioConnectionError,
)
from .const import CONF_API_TOKEN, DEFAULT_HOST, DEFAULT_PORT, DOMAIN

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


class LMStudioConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LM Studio."""

    VERSION = 1

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
