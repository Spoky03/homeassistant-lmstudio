"""Number platform for LM Studio per-model load options."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode, RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_EFFECTIVE_CONTEXT_LENGTH,
    ATTR_USES_DEFAULT,
    DOMAIN,
    UNIQUE_ID_CONTEXT_LENGTH_SUFFIX,
)
from .coordinator import LMStudioDataUpdateCoordinator, LMStudioModel
from .entity import LMStudioEntity
from .helpers import resolve_model_load_context_length


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LM Studio number entities."""
    coordinator: LMStudioDataUpdateCoordinator = hass.data[DOMAIN][
        entry.entry_id
    ].models

    @callback
    def _create_entities() -> list[NumberEntity]:
        return [
            LMStudioModelContextLengthNumber(coordinator, model)
            for model in coordinator.data or []
        ]

    async_add_entities(_create_entities())


class LMStudioModelContextLengthNumber(LMStudioEntity, RestoreNumber):
    """Number entity to override context length when loading a model."""

    _attr_translation_key = "model_context_length"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = True
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "tokens"

    def __init__(
        self,
        coordinator: LMStudioDataUpdateCoordinator,
        model: LMStudioModel,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, model)
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{model.key}_"
            f"{UNIQUE_ID_CONTEXT_LENGTH_SUFFIX}"
        )

    async def async_added_to_hass(self) -> None:
        """Restore number state."""
        await super().async_added_to_hass()
        if (last_number_data := await self.async_get_last_number_data()) is not None:
            self._attr_native_value = last_number_data.native_value
        else:
            self._attr_native_value = 0

    @property
    def available(self) -> bool:
        """Return whether the model still exists."""
        return super().available and self.model is not None

    @property
    def native_max_value(self) -> float:
        """Return the maximum context length for this model."""
        model = self.model
        if model and model.max_context_length:
            return float(model.max_context_length)
        return 131072.0

    @property
    def extra_state_attributes(self) -> dict[str, bool | int | None]:
        """Return effective load settings."""
        entry = self.coordinator.config_entry
        effective = resolve_model_load_context_length(self.hass, entry, self.model_key)
        value = self.native_value or 0
        return {
            ATTR_USES_DEFAULT: value <= 0,
            ATTR_EFFECTIVE_CONTEXT_LENGTH: effective,
        }

    async def async_set_native_value(self, value: float) -> None:
        """Set the context length override."""
        self._attr_native_value = value
        self.async_write_ha_state()
