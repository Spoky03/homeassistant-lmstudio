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
    ATTR_DOWNLOAD_COMPLETED_AT,
    ATTR_DOWNLOAD_ERROR,
    ATTR_DOWNLOAD_MODEL,
    ATTR_DOWNLOAD_PROGRESS,
    ATTR_DOWNLOAD_STARTED_AT,
    ATTR_DOWNLOADED_BYTES,
    ATTR_FORMAT,
    ATTR_INSTANCE_IDS,
    ATTR_JOB_ID,
    ATTR_KEY,
    ATTR_LOADED,
    ATTR_MAX_CONTEXT_LENGTH,
    ATTR_MODEL_TYPE,
    ATTR_PARAMS,
    ATTR_PUBLISHER,
    ATTR_QUANTIZATION,
    ATTR_SIZE_BYTES,
    ATTR_TOTAL_SIZE_BYTES,
    DOMAIN,
)
from .coordinator import LMStudioDataUpdateCoordinator, LMStudioModel
from .download_coordinator import (
    LMStudioDownloadCoordinator,
    LMStudioDownloadJob,
)
from .entity import LMStudioEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LM Studio sensors."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator = runtime.models
    download_coordinator = runtime.downloads
    tracked_job_entities: dict[str, LMStudioDownloadJobSensor] = {}

    @callback
    def _create_entities() -> list[SensorEntity]:
        return [
            LMStudioModelCountSensor(coordinator),
            LMStudioActiveDownloadsSensor(download_coordinator, coordinator),
            *(
                LMStudioModelSensor(coordinator, model)
                for model in coordinator.data or []
            ),
        ]

    async_add_entities(_create_entities())

    @callback
    def _add_job_entity(job_id: str) -> None:
        if job_id in tracked_job_entities:
            return
        job = download_coordinator.jobs.get(job_id)
        entity = LMStudioDownloadJobSensor(
            download_coordinator,
            job_id,
            job.model if job else job_id,
        )
        tracked_job_entities[job_id] = entity
        async_add_entities([entity])

    @callback
    def _handle_download_update() -> None:
        active_job_ids = set(download_coordinator.data or {})
        for job_id in list(tracked_job_entities):
            if job_id not in active_job_ids:
                entity = tracked_job_entities.pop(job_id)
                if entity.hass:
                    entity.hass.async_create_task(entity.async_remove())

    download_coordinator.async_add_listener(_handle_download_update)
    entry.async_on_unload(
        download_coordinator.async_add_new_job_listener(_add_job_entity)
    )


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


class LMStudioActiveDownloadsSensor(
    CoordinatorEntity[LMStudioDownloadCoordinator], SensorEntity
):
    """Sensor showing the number of active download jobs."""

    _attr_has_entity_name = True
    _attr_translation_key = "active_downloads"
    _attr_unique_id: str

    def __init__(
        self,
        coordinator: LMStudioDownloadCoordinator,
        models_coordinator: LMStudioDataUpdateCoordinator,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_active_downloads"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=models_coordinator.config_entry.title,
            manufacturer="LM Studio",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> int:
        """Return active download count."""
        return len(self.coordinator.jobs)

    @property
    def extra_state_attributes(self) -> dict[str, list[dict[str, str | float | None]]]:
        """Return active download job details."""
        jobs = []
        for job in (self.coordinator.data or {}).values():
            jobs.append(
                {
                    ATTR_JOB_ID: job.job_id,
                    ATTR_DOWNLOAD_MODEL: job.model,
                    "status": job.status,
                    ATTR_DOWNLOAD_PROGRESS: job.progress,
                    ATTR_TOTAL_SIZE_BYTES: job.total_size_bytes,
                    ATTR_DOWNLOADED_BYTES: job.downloaded_bytes,
                }
            )
        return {"jobs": jobs}


class LMStudioDownloadJobSensor(
    CoordinatorEntity[LMStudioDownloadCoordinator], SensorEntity
):
    """Sensor showing progress for a single download job."""

    _attr_has_entity_name = True
    _attr_translation_key = "download_progress"
    _attr_native_unit_of_measurement = "%"

    def __init__(
        self,
        coordinator: LMStudioDownloadCoordinator,
        job_id: str,
        job_name: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._job_id = job_id
        self._attr_name = job_name
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_download_{job_id}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=coordinator.config_entry.title,
            manufacturer="LM Studio",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def job(self) -> LMStudioDownloadJob | None:
        """Return the tracked download job."""
        return (self.coordinator.data or {}).get(self._job_id)

    @property
    def available(self) -> bool:
        """Return whether the job is still active."""
        return super().available and self.job is not None

    @property
    def native_value(self) -> float | None:
        """Return download progress percentage."""
        job = self.job
        return job.progress if job else None

    @property
    def extra_state_attributes(self) -> dict[str, str | int | float | None]:
        """Return download job metadata."""
        job = self.job
        if not job:
            return {}
        return {
            ATTR_JOB_ID: job.job_id,
            ATTR_DOWNLOAD_MODEL: job.model,
            "status": job.status,
            ATTR_TOTAL_SIZE_BYTES: job.total_size_bytes,
            ATTR_DOWNLOADED_BYTES: job.downloaded_bytes,
            ATTR_DOWNLOAD_STARTED_AT: job.started_at,
            ATTR_DOWNLOAD_COMPLETED_AT: job.completed_at,
            ATTR_DOWNLOAD_ERROR: job.error,
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
