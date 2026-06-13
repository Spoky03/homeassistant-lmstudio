"""Runtime data for the LM Studio integration."""

from __future__ import annotations

from dataclasses import dataclass

from .coordinator import LMStudioDataUpdateCoordinator
from .download_coordinator import LMStudioDownloadCoordinator


@dataclass
class LMStudioRuntimeData:
    """Data stored in hass.data for a config entry."""

    models: LMStudioDataUpdateCoordinator
    downloads: LMStudioDownloadCoordinator
