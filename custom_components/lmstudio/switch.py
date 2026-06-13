"""Switch platform for LM Studio model load/unload."""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import LMStudioApiError
from .const import DOMAIN
from .coordinator import LMStudioDataUpdateCoordinator, LMStudioModel
from .entity import LMStudioEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LM Studio switches."""
    coordinator: LMStudioDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    @callback
    def _create_entities() -> list[SwitchEntity]:
        return [
            LMStudioModelLoadSwitch(coordinator, model)
            for model in coordinator.data or []
        ]

    async_add_entities(_create_entities())


class LMStudioModelLoadSwitch(LMStudioEntity, SwitchEntity):
    """Switch to load or unload an LM Studio model."""

    _attr_translation_key = "model_load"
    _attr_entity_registry_enabled_default = True

    def __init__(
        self,
        coordinator: LMStudioDataUpdateCoordinator,
        model: LMStudioModel,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, model)

    @property
    def available(self) -> bool:
        """Return whether the model still exists."""
        return super().available and self.model is not None

    @property
    def is_on(self) -> bool | None:
        """Return whether the model is loaded."""
        model = self.model
        return model.loaded if model else None

    async def async_turn_on(self, **kwargs: object) -> None:
        """Load the model."""
        model = self.model
        if not model or model.loaded:
            return
        try:
            await self.coordinator.client.async_load_model(model.key)
        except LMStudioApiError as err:
            _LOGGER.error("Failed to load model %s: %s", model.key, err)
            raise
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: object) -> None:
        """Unload all instances of the model."""
        model = self.model
        if not model or not model.instance_ids:
            return
        try:
            for instance_id in model.instance_ids:
                await self.coordinator.client.async_unload_model(instance_id)
        except LMStudioApiError as err:
            _LOGGER.error("Failed to unload model %s: %s", model.key, err)
            raise
        await self.coordinator.async_request_refresh()
