"""Base entity for LM Studio."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LMStudioDataUpdateCoordinator, LMStudioModel


class LMStudioEntity(CoordinatorEntity[LMStudioDataUpdateCoordinator]):
    """Base class for LM Studio entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LMStudioDataUpdateCoordinator,
        model: LMStudioModel,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.model_key = model.key
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{model.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, model.key)},
            name=model.display_name,
            manufacturer=model.publisher or "LM Studio",
            model=model.params_string or model.architecture,
            via_device=(DOMAIN, coordinator.config_entry.entry_id),
        )

    @property
    def model(self) -> LMStudioModel | None:
        """Return the current model data."""
        for item in self.coordinator.data or []:
            if item.key == self.model_key:
                return item
        return None
