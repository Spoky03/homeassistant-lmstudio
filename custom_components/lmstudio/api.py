"""LM Studio REST API client."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

_LOGGER = logging.getLogger(__name__)

TIMEOUT = ClientTimeout(total=30)


class LMStudioApiError(Exception):
    """Base exception for LM Studio API errors."""


class LMStudioConnectionError(LMStudioApiError):
    """Raised when the LM Studio server cannot be reached."""


class LMStudioAuthError(LMStudioApiError):
    """Raised when authentication fails."""


class LMStudioClient:
    """Async client for the LM Studio v1 REST API."""

    def __init__(
        self,
        session: ClientSession,
        host: str,
        port: int,
        api_token: str | None = None,
    ) -> None:
        """Initialize the client."""
        self._session = session
        self._base_url = f"http://{host}:{port}/api/v1"
        self._headers: dict[str, str] = {}
        if api_token:
            self._headers["Authorization"] = f"Bearer {api_token}"

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> Any:
        """Make an API request."""
        url = f"{self._base_url}{path}"
        try:
            async with self._session.request(
                method,
                url,
                headers=self._headers,
                json=json,
                timeout=TIMEOUT,
            ) as response:
                if response.status == 401:
                    raise LMStudioAuthError("Invalid API token")
                if response.status >= 400:
                    body = await response.text()
                    raise LMStudioApiError(
                        f"API error {response.status}: {body[:200]}"
                    )
                if response.content_length == 0:
                    return None
                return await response.json()
        except ClientError as err:
            raise LMStudioConnectionError(str(err)) from err

    async def async_get_models(self) -> list[dict[str, Any]]:
        """Return all models from the server."""
        data = await self._request("GET", "/models")
        if not isinstance(data, dict):
            raise LMStudioApiError("Unexpected models response")
        models = data.get("models", [])
        if not isinstance(models, list):
            raise LMStudioApiError("Unexpected models list")
        return models

    async def async_load_model(
        self,
        model_key: str,
        *,
        context_length: int | None = None,
    ) -> dict[str, Any]:
        """Load a model onto the server."""
        payload: dict[str, Any] = {"model": model_key}
        if context_length is not None:
            payload["context_length"] = context_length
        result = await self._request("POST", "/models/load", json=payload)
        if not isinstance(result, dict):
            raise LMStudioApiError("Unexpected load response")
        return result

    async def async_unload_model(self, instance_id: str) -> dict[str, Any]:
        """Unload a loaded model instance."""
        result = await self._request(
            "POST",
            "/models/unload",
            json={"instance_id": instance_id},
        )
        if not isinstance(result, dict):
            raise LMStudioApiError("Unexpected unload response")
        return result
