"""Services for the LM Studio integration."""

from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv, selector, service

from .api import LMStudioApiError
from .const import CONF_CONFIG_ENTRY, CONF_MODEL, DOMAIN, SERVICE_DOWNLOAD_MODEL
from .runtime import LMStudioRuntimeData

_LOGGER = logging.getLogger(__name__)

DOWNLOAD_MODEL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CONFIG_ENTRY): selector.ConfigEntrySelector(
            {"integration": DOMAIN}
        ),
        vol.Required(CONF_MODEL): cv.string,
    }
)


def _get_runtime_data(
    hass: HomeAssistant, entry: ConfigEntry
) -> LMStudioRuntimeData:
    """Return runtime data for a config entry."""
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if not isinstance(data, LMStudioRuntimeData):
        raise HomeAssistantError("LM Studio is not loaded")
    return data


async def async_download_model(call: ServiceCall) -> None:
    """Start downloading a model."""
    entry = service.async_get_config_entry(
        call.hass, DOMAIN, call.data[CONF_CONFIG_ENTRY]
    )
    model = call.data[CONF_MODEL]
    runtime = _get_runtime_data(call.hass, entry)

    try:
        job = await runtime.downloads.async_start_download(model)
    except LMStudioApiError as err:
        raise ServiceValidationError(f"Failed to start download: {err}") from err

    _LOGGER.info(
        "Started LM Studio download for %s (job_id=%s, entry=%s)",
        model,
        job.job_id,
        entry.entry_id,
    )


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register LM Studio services."""
    if hass.services.has_service(DOMAIN, SERVICE_DOWNLOAD_MODEL):
        return

    hass.services.async_register(
        DOMAIN,
        SERVICE_DOWNLOAD_MODEL,
        async_download_model,
        schema=DOWNLOAD_MODEL_SCHEMA,
    )
