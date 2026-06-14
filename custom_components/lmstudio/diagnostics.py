"""Diagnostics support for the LM Studio integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

from .const import CONF_API_TOKEN, DOMAIN
from .coordinator import LMStudioModel
from .download_coordinator import LMStudioDownloadJob
from .helpers import (
    get_chat_max_history,
    get_chat_max_tokens,
    get_chat_model,
    get_chat_prompt,
    get_chat_temperature,
    get_load_context_length,
    get_load_flash_attention,
    get_scan_interval,
)

TO_REDACT = {CONF_API_TOKEN}


def _model_snapshot(model: LMStudioModel) -> dict[str, Any]:
    """Return a diagnostics-safe model snapshot."""
    return {
        "key": model.key,
        "display_name": model.display_name,
        "type": model.model_type,
        "loaded": model.loaded,
        "instance_ids": model.instance_ids,
        "publisher": model.publisher,
        "architecture": model.architecture,
        "format": model.format,
        "params_string": model.params_string,
        "size_bytes": model.size_bytes,
        "max_context_length": model.max_context_length,
        "quantization_name": model.quantization_name,
    }


def _download_snapshot(job: LMStudioDownloadJob) -> dict[str, Any]:
    """Return a diagnostics-safe download job snapshot."""
    return {
        "job_id": job.job_id,
        "model": job.model,
        "status": job.status,
        "progress": job.progress,
        "downloaded_bytes": job.downloaded_bytes,
        "total_size_bytes": job.total_size_bytes,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "error": job.error,
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    diagnostics: dict[str, Any] = {
        "config_entry": {
            "title": entry.title,
            "unique_id": entry.unique_id,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "connection": {
            "host": entry.data[CONF_HOST],
            "port": entry.data[CONF_PORT],
            "api_token_configured": bool(entry.data.get(CONF_API_TOKEN)),
        },
        "resolved_options": {
            "scan_interval": get_scan_interval(entry),
            "context_length": get_load_context_length(entry),
            "flash_attention": get_load_flash_attention(entry),
            "chat_model": get_chat_model(entry),
            "chat_temperature": get_chat_temperature(entry),
            "chat_max_tokens": get_chat_max_tokens(entry),
            "chat_max_history": get_chat_max_history(entry),
            "chat_prompt_configured": bool(get_chat_prompt(entry)),
        },
    }

    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if runtime is None:
        diagnostics["runtime"] = {"loaded": False}
        return diagnostics

    models_coordinator = runtime.models
    diagnostics["runtime"] = {"loaded": True}
    diagnostics["models_coordinator"] = {
        "last_update_success": models_coordinator.last_update_success,
        "last_exception": (
            str(models_coordinator.last_exception)
            if models_coordinator.last_exception
            else None
        ),
        "model_count": len(models_coordinator.data or []),
    }
    diagnostics["models"] = [
        _model_snapshot(model) for model in models_coordinator.data or []
    ]

    download_jobs = list(runtime.downloads.jobs.values())
    diagnostics["download_jobs"] = [
        _download_snapshot(job) for job in download_jobs
    ]

    return diagnostics
