"""Base entity for LM Studio model entities."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LMStudioDataUpdateCoordinator, LMStudioModel
from .runtime import LMStudioRuntimeData


class LMStudioHubEntity(Entity):
    """Base entity attached to the LM Studio hub device."""

    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, runtime: LMStudioRuntimeData) -> None:
        """Initialize."""
        self.entry = entry
        self.runtime = runtime
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="LM Studio",
            entry_type=DeviceEntryType.SERVICE,
        )


class LMStudioEntity(CoordinatorEntity[LMStudioDataUpdateCoordinator]):
    """Base class for LM Studio model entities."""

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
