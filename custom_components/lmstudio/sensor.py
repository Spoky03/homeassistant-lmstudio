"""Sensor platform for LM Studio."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_ARCHITECTURE,
    ATTR_DISPLAY_NAME,
    ATTR_FORMAT,
    ATTR_INSTANCE_IDS,
    ATTR_KEY,
    ATTR_LOADED,
    ATTR_MAX_CONTEXT_LENGTH,
    ATTR_MODEL_TYPE,
    ATTR_PARAMS,
    ATTR_PUBLISHER,
    ATTR_QUANTIZATION,
    ATTR_SIZE_BYTES,
    DOMAIN,
)
from .coordinator import LMStudioDataUpdateCoordinator, LMStudioModel
from .entity import LMStudioEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LM Studio sensors."""
    coordinator: LMStudioDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    @callback
    def _create_entities() -> list[SensorEntity]:
        return [
            LMStudioModelCountSensor(coordinator),
            *(
                LMStudioModelSensor(coordinator, model)
                for model in coordinator.data or []
            ),
        ]

    async_add_entities(_create_entities())


class LMStudioModelCountSensor(CoordinatorEntity[LMStudioDataUpdateCoordinator], SensorEntity):
    """Sensor showing total and loaded model counts."""

    _attr_has_entity_name = True
    _attr_translation_key = "model_count"
    _attr_unique_id: str

    def __init__(self, coordinator: LMStudioDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_model_count"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=coordinator.config_entry.title,
            manufacturer="LM Studio",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> int:
        """Return total model count."""
        return len(self.coordinator.data or [])

    @property
    def extra_state_attributes(self) -> dict[str, int]:
        """Return loaded model count."""
        loaded = sum(1 for model in self.coordinator.data or [] if model.loaded)
        return {
            "loaded_models": loaded,
            "available_models": self.native_value,
        }


class LMStudioModelSensor(LMStudioEntity, SensorEntity):
    """Sensor exposing metadata for a single LM Studio model."""

    _attr_translation_key = "model_info"
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
    def native_value(self) -> str | None:
        """Return model type."""
        model = self.model
        return model.model_type if model else None

    @property
    def extra_state_attributes(self) -> dict[str, str | int | bool | list[str] | None]:
        """Return model metadata."""
        model = self.model
        if not model:
            return {}
        return {
            ATTR_KEY: model.key,
            ATTR_DISPLAY_NAME: model.display_name,
            ATTR_MODEL_TYPE: model.model_type,
            ATTR_PUBLISHER: model.publisher,
            ATTR_ARCHITECTURE: model.architecture,
            ATTR_FORMAT: model.format,
            ATTR_PARAMS: model.params_string,
            ATTR_SIZE_BYTES: model.size_bytes,
            ATTR_QUANTIZATION: model.quantization_name,
            ATTR_MAX_CONTEXT_LENGTH: model.max_context_length,
            ATTR_LOADED: model.loaded,
            ATTR_INSTANCE_IDS: model.instance_ids,
        }
