"""Data update coordinator for LM Studio."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LMStudioApiError, LMStudioClient, LMStudioConnectionError
from .const import DOMAIN
from .helpers import get_scan_interval

_LOGGER = logging.getLogger(__name__)


@dataclass
class LMStudioModel:
    """Normalized model data from the LM Studio API."""

    key: str
    display_name: str
    model_type: str
    publisher: str | None
    architecture: str | None
    format: str | None
    params_string: str | None
    size_bytes: int | None
    max_context_length: int | None
    quantization_name: str | None
    loaded: bool
    instance_ids: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


def _parse_model(raw: dict[str, Any]) -> LMStudioModel:
    """Parse a model dict from the API."""
    loaded_instances = raw.get("loaded_instances") or []
    instance_ids = [
        instance["id"]
        for instance in loaded_instances
        if isinstance(instance, dict) and instance.get("id")
    ]
    quantization = raw.get("quantization") or {}
    quantization_name = None
    if isinstance(quantization, dict):
        quantization_name = quantization.get("name")

    return LMStudioModel(
        key=str(raw.get("key", "")),
        display_name=str(raw.get("display_name") or raw.get("key", "")),
        model_type=str(raw.get("type", "unknown")),
        publisher=raw.get("publisher"),
        architecture=raw.get("architecture"),
        format=raw.get("format"),
        params_string=raw.get("params_string"),
        size_bytes=raw.get("size_bytes"),
        max_context_length=raw.get("max_context_length"),
        quantization_name=quantization_name,
        loaded=bool(instance_ids),
        instance_ids=instance_ids,
        raw=raw,
    )


class LMStudioDataUpdateCoordinator(DataUpdateCoordinator[list[LMStudioModel]]):
    """Coordinator that polls LM Studio for model state."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: LMStudioClient,
        entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        self.client = client
        self.config_entry = entry
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=get_scan_interval(entry)),
        )
        self._known_models: list[LMStudioModel] = []

    async def _async_update_data(self) -> list[LMStudioModel]:
        """Fetch models from LM Studio.

        Keeps the last known model list on transient errors so entities
        stay available and the conversation/AI task agents remain
        functional even when LM Studio is briefly unreachable.
        """
        try:
            raw_models = await self.client.async_get_models()
        except LMStudioConnectionError as err:
            _LOGGER.debug("LM Studio temporarily unreachable: %s", err)
            if self._known_models:
                return self._known_models
            raise UpdateFailed(f"Cannot connect to LM Studio: {err}") from err
        except LMStudioApiError as err:
            _LOGGER.debug("LM Studio API returned error: %s", err)
            if self._known_models:
                return self._known_models
            raise UpdateFailed(str(err)) from err

        self._known_models = [
            _parse_model(model) for model in raw_models if model.get("key")
        ]
        return self._known_models
