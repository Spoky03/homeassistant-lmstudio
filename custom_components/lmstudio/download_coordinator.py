"""Download job coordinator for LM Studio."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from typing import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LMStudioApiError, LMStudioClient, LMStudioConnectionError
from .const import DOMAIN, DOWNLOAD_TERMINAL_STATUSES, DOWNLOAD_UPDATE_INTERVAL_SECONDS
from .coordinator import LMStudioDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class LMStudioDownloadJob:
    """Normalized download job data from the LM Studio API."""

    job_id: str
    model: str
    status: str
    total_size_bytes: int | None = None
    downloaded_bytes: int | None = None
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None

    @property
    def progress(self) -> float | None:
        """Return download progress as a percentage."""
        if (
            self.total_size_bytes
            and self.downloaded_bytes is not None
            and self.total_size_bytes > 0
        ):
            return round(
                100 * self.downloaded_bytes / self.total_size_bytes,
                1,
            )
        return None

    @property
    def is_terminal(self) -> bool:
        """Return whether the job has finished."""
        return self.status.lower() in DOWNLOAD_TERMINAL_STATUSES


def _parse_download_job(
    raw: dict[str, Any],
    *,
    model: str | None = None,
) -> LMStudioDownloadJob:
    """Parse a download job dict from the API."""
    return LMStudioDownloadJob(
        job_id=str(raw.get("job_id", "")),
        model=model or str(raw.get("model") or raw.get("model_key") or "unknown"),
        status=str(raw.get("status", "unknown")),
        total_size_bytes=raw.get("total_size_bytes"),
        downloaded_bytes=raw.get("downloaded_bytes"),
        started_at=raw.get("started_at"),
        completed_at=raw.get("completed_at"),
        error=raw.get("error"),
    )


class LMStudioDownloadCoordinator(DataUpdateCoordinator[dict[str, LMStudioDownloadJob]]):
    """Coordinator that tracks active LM Studio download jobs."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: LMStudioClient,
        entry: ConfigEntry,
        models_coordinator: LMStudioDataUpdateCoordinator,
    ) -> None:
        """Initialize."""
        self.client = client
        self.config_entry = entry
        self.models_coordinator = models_coordinator
        self._jobs: dict[str, LMStudioDownloadJob] = {}
        self._new_job_callbacks: list[Callable[[str], None]] = []
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_downloads",
            update_interval=None,
        )

    @property
    def jobs(self) -> dict[str, LMStudioDownloadJob]:
        """Return tracked download jobs."""
        return self._jobs

    def async_add_new_job_listener(
        self, listener: Callable[[str], None]
    ) -> Callable[[], None]:
        """Listen for new download jobs."""
        self._new_job_callbacks.append(listener)

        @callback
        def remove_listener() -> None:
            self._new_job_callbacks.remove(listener)

        return remove_listener

    @callback
    def _fire_new_job(self, job_id: str) -> None:
        """Notify listeners that a new job was created."""
        for listener in self._new_job_callbacks:
            listener(job_id)

    async def async_start_download(self, model: str) -> LMStudioDownloadJob:
        """Start downloading a model and track the job."""
        try:
            raw = await self.client.async_download_model(model)
        except LMStudioConnectionError as err:
            raise LMStudioApiError(f"Cannot connect to LM Studio: {err}") from err

        job = _parse_download_job(raw, model=model)
        self._jobs[job.job_id] = job
        self.update_interval = timedelta(seconds=DOWNLOAD_UPDATE_INTERVAL_SECONDS)
        await self.async_request_refresh()
        self._fire_new_job(job.job_id)
        return job

    async def _async_update_data(self) -> dict[str, LMStudioDownloadJob]:
        """Refresh status for all tracked download jobs."""
        if not self._jobs:
            self.update_interval = None
            return {}

        updated: dict[str, LMStudioDownloadJob] = {}
        completed = False

        for job_id, current in list(self._jobs.items()):
            try:
                raw = await self.client.async_get_download_status(job_id)
            except LMStudioConnectionError as err:
                raise UpdateFailed(f"Cannot connect to LM Studio: {err}") from err
            except LMStudioApiError as err:
                _LOGGER.warning("Failed to fetch download status for %s: %s", job_id, err)
                updated[job_id] = current
                continue

            job = _parse_download_job(raw, model=current.model)
            updated[job_id] = job

            if job.is_terminal:
                completed = completed or job.status.lower() == "completed"
                del self._jobs[job_id]

        if not self._jobs:
            self.update_interval = None

        if completed:
            await self.models_coordinator.async_request_refresh()

        return updated
