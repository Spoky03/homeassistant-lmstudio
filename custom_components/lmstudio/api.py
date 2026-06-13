"""LM Studio REST API client."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

_LOGGER = logging.getLogger(__name__)

TIMEOUT = ClientTimeout(total=30)
CHAT_TIMEOUT = ClientTimeout(total=120)


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
        self._openai_base_url = f"http://{host}:{port}/v1"
        self._headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_token:
            self._headers["Authorization"] = f"Bearer {api_token}"

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        base_url: str | None = None,
        timeout: ClientTimeout | None = None,
    ) -> Any:
        """Make an API request."""
        url = f"{base_url or self._base_url}{path}"
        try:
            async with self._session.request(
                method,
                url,
                headers=self._headers,
                json=json,
                timeout=timeout or TIMEOUT,
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
        flash_attention: bool | None = None,
    ) -> dict[str, Any]:
        """Load a model onto the server."""
        payload: dict[str, Any] = {"model": model_key}
        if context_length is not None:
            payload["context_length"] = context_length
        if flash_attention is not None:
            payload["flash_attention"] = flash_attention
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

    async def async_download_model(self, model: str) -> dict[str, Any]:
        """Start downloading a model from the LM Studio catalog."""
        result = await self._request(
            "POST",
            "/models/download",
            json={"model": model},
        )
        if not isinstance(result, dict):
            raise LMStudioApiError("Unexpected download response")
        if not result.get("job_id"):
            raise LMStudioApiError("Download response missing job_id")
        return result

    async def async_get_download_status(self, job_id: str) -> dict[str, Any]:
        """Return the status of a download job."""
        result = await self._request("GET", f"/models/download/status/{job_id}")
        if not isinstance(result, dict):
            raise LMStudioApiError("Unexpected download status response")
        return result

    async def async_chat_completion(
        self,
        messages: list[dict[str, Any]],
        model: str,
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call the OpenAI-compatible chat completions endpoint."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if response_format is not None:
            payload["response_format"] = response_format

        result = await self._request(
            "POST",
            "/chat/completions",
            json=payload,
            base_url=self._openai_base_url,
            timeout=CHAT_TIMEOUT,
        )
        if not isinstance(result, dict):
            raise LMStudioApiError("Unexpected chat completion response")
        return result
