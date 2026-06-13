"""Binary sensor platform for LM Studio."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import LMStudioDataUpdateCoordinator, LMStudioModel
from .entity import LMStudioEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LM Studio binary sensors."""
    coordinator: LMStudioDataUpdateCoordinator = hass.data[DOMAIN][
        entry.entry_id
    ].models

    @callback
    def _create_entities() -> list[BinarySensorEntity]:
        return [
            LMStudioModelLoadedBinarySensor(coordinator, model)
            for model in coordinator.data or []
        ]

    async_add_entities(_create_entities())


class LMStudioModelLoadedBinarySensor(LMStudioEntity, BinarySensorEntity):
    """Binary sensor indicating whether a model is loaded."""

    _attr_translation_key = "model_loaded"
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
        """Return loaded state."""
        model = self.model
        return model.loaded if model else None
