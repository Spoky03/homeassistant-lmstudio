"""Switch platform for LM Studio model load/unload."""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import LMStudioApiError
from .const import (
    ATTR_EFFECTIVE_FLASH_ATTENTION,
    ATTR_OVERRIDE,
    ATTR_USES_DEFAULT,
    DOMAIN,
    UNIQUE_ID_FLASH_ATTENTION_SUFFIX,
)
from .coordinator import LMStudioDataUpdateCoordinator, LMStudioModel
from .entity import LMStudioEntity
from .helpers import (
    get_load_flash_attention,
    resolve_model_load_context_length,
    resolve_model_load_flash_attention,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LM Studio switches."""
    coordinator: LMStudioDataUpdateCoordinator = hass.data[DOMAIN][
        entry.entry_id
    ].models

    @callback
    def _create_entities() -> list[SwitchEntity]:
        entities: list[SwitchEntity] = []
        for model in coordinator.data or []:
            entities.append(LMStudioModelLoadSwitch(coordinator, model))
            entities.append(LMStudioModelFlashAttentionSwitch(coordinator, model))
        return entities

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
            entry = self.coordinator.config_entry
            context_length = resolve_model_load_context_length(
                self.hass, entry, model.key
            )
            flash_attention = resolve_model_load_flash_attention(
                self.hass, entry, model.key
            )
            await self.coordinator.client.async_load_model(
                model.key,
                context_length=context_length,
                flash_attention=flash_attention,
            )
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


class LMStudioModelFlashAttentionSwitch(LMStudioEntity, SwitchEntity, RestoreEntity):
    """Switch to override flash attention when loading a model."""

    _attr_translation_key = "model_flash_attention"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = True

    def __init__(
        self,
        coordinator: LMStudioDataUpdateCoordinator,
        model: LMStudioModel,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, model)
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{model.key}_"
            f"{UNIQUE_ID_FLASH_ATTENTION_SUFFIX}"
        )
        self._override: bool | None = None

    async def async_added_to_hass(self) -> None:
        """Restore override state."""
        await super().async_added_to_hass()
        if state := await self.async_get_last_state():
            if state.attributes.get(ATTR_USES_DEFAULT, True):
                self._override = None
            else:
                self._override = state.state == "on"

    @property
    def available(self) -> bool:
        """Return whether the model still exists."""
        return super().available and self.model is not None

    @property
    def is_on(self) -> bool | None:
        """Return effective flash attention value."""
        if self._override is not None:
            return self._override
        return get_load_flash_attention(self.coordinator.config_entry)

    @property
    def extra_state_attributes(self) -> dict[str, bool | None]:
        """Return override metadata."""
        entry = self.coordinator.config_entry
        return {
            ATTR_USES_DEFAULT: self._override is None,
            ATTR_OVERRIDE: self._override,
            ATTR_EFFECTIVE_FLASH_ATTENTION: resolve_model_load_flash_attention(
                self.hass, entry, self.model_key
            ),
        }

    async def async_turn_on(self, **kwargs: object) -> None:
        """Enable flash attention for this model."""
        self._override = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: object) -> None:
        """Disable flash attention for this model."""
        self._override = False
        self.async_write_ha_state()
