"""A tiny async client for the single Mistral endpoint the bot needs."""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Sequence
from typing import Any

import httpx

from . import __version__
from .config import Settings
from .memory import ChatMessage

LOGGER = logging.getLogger(__name__)
CHAT_COMPLETIONS_URL = "https://api.mistral.ai/v1/chat/completions"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class MistralAPIError(RuntimeError):
    """A sanitized Mistral failure safe to route by status code."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class MistralClient:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        max_attempts: int = 3,
    ) -> None:
        self._settings = settings
        self._max_attempts = max_attempts
        self._semaphore = asyncio.Semaphore(2)
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.mistral_timeout_seconds),
            transport=transport,
            headers={
                "Authorization": f"Bearer {settings.mistral_api_key}",
                "Content-Type": "application/json",
                "User-Agent": f"self-tg-approve/{__version__}",
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def chat(
        self,
        *,
        system_prompt: str,
        history: Sequence[ChatMessage],
        user_text: str,
    ) -> str:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            *({"role": item["role"], "content": item["content"]} for item in history),
            {"role": "user", "content": user_text},
        ]
        payload: dict[str, Any] = {
            "model": self._settings.mistral_model,
            "messages": messages,
            "max_tokens": self._settings.mistral_max_tokens,
            "temperature": self._settings.mistral_temperature,
            "reasoning_effort": "none",
            "stream": False,
        }

        async with self._semaphore:
            response = await self._post_with_retry(payload)
        return self._extract_text(response)

    async def _post_with_retry(self, payload: dict[str, Any]) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self._max_attempts):
            try:
                response = await self._client.post(CHAT_COMPLETIONS_URL, json=payload)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                if attempt + 1 >= self._max_attempts:
                    break
                await asyncio.sleep(self._retry_delay(attempt, None))
                continue

            if response.status_code < 400:
                return response
            if (
                response.status_code in RETRYABLE_STATUS_CODES
                and attempt + 1 < self._max_attempts
            ):
                LOGGER.warning(
                    "Mistral временно недоступен: HTTP %s, попытка %s/%s",
                    response.status_code,
                    attempt + 1,
                    self._max_attempts,
                )
                await asyncio.sleep(self._retry_delay(attempt, response))
                continue
            raise MistralAPIError(
                f"Mistral API вернул HTTP {response.status_code}",
                status_code=response.status_code,
            )

        raise MistralAPIError("Не удалось соединиться с Mistral API") from last_error

    @staticmethod
    def _retry_delay(attempt: int, response: httpx.Response | None) -> float:
        if response is not None:
            raw_retry_after = response.headers.get("Retry-After")
            if raw_retry_after:
                try:
                    return min(max(float(raw_retry_after), 0.0), 8.0)
                except ValueError:
                    pass
        return min(0.75 * (2**attempt) + random.uniform(0.0, 0.25), 4.0)

    @staticmethod
    def _extract_text(response: httpx.Response) -> str:
        try:
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise MistralAPIError("Mistral API вернул неожиданный ответ") from exc

        if isinstance(content, str):
            text = content.strip()
        elif isinstance(content, list):
            text = "".join(
                str(part.get("text", "")) for part in content if isinstance(part, dict)
            ).strip()
        else:
            text = ""

        if not text:
            raise MistralAPIError("Mistral API вернул пустой ответ")
        return text
