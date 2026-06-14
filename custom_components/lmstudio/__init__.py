"""The LM Studio integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LMStudioApiError, LMStudioClient, LMStudioConnectionError
from .const import CONF_API_TOKEN, DOMAIN
from .coordinator import LMStudioDataUpdateCoordinator
from .download_coordinator import LMStudioDownloadCoordinator
from .runtime import LMStudioRuntimeData
from .services import async_setup_services
_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.AI_TASK,
    Platform.BINARY_SENSOR,
    Platform.CONVERSATION,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the LM Studio integration."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LM Studio from a config entry."""
    client = LMStudioClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data.get(CONF_API_TOKEN) or None,
    )
    models_coordinator = LMStudioDataUpdateCoordinator(hass, client, entry)
    downloads_coordinator = LMStudioDownloadCoordinator(
        hass, client, entry, models_coordinator
    )

    try:
        await models_coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        raise
    except (LMStudioConnectionError, LMStudioApiError) as err:
        raise ConfigEntryNotReady(
            f"Cannot connect to LM Studio: {err}"
        ) from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = LMStudioRuntimeData(
        models=models_coordinator,
        downloads=downloads_coordinator,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
