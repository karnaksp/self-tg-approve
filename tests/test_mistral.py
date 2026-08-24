from __future__ import annotations

import json
import unittest

import httpx

from self_tg_approve.config import Settings
from self_tg_approve.mistral import MistralAPIError, MistralClient


def settings() -> Settings:
    return Settings(
        telegram_token="telegram-secret",
        channel_id=-100123,
        admin_id=42,
        mistral_api_key="mistral-secret",
    )


class MistralClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_chat_sends_bounded_completion_request(self) -> None:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["authorization"] = request.headers["Authorization"]
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": " Готова! "}}]},
            )

        client = MistralClient(
            settings(), transport=httpx.MockTransport(handler), max_attempts=1
        )
        try:
            answer = await client.chat(
                system_prompt="system",
                history=[{"role": "assistant", "content": "before"}],
                user_text="hello",
            )
        finally:
            await client.close()

        self.assertEqual(answer, "Готова!")
        self.assertEqual(captured["url"], "https://api.mistral.ai/v1/chat/completions")
        self.assertEqual(captured["authorization"], "Bearer mistral-secret")
        body = captured["body"]
        assert isinstance(body, dict)
        self.assertEqual(body["model"], "mistral-small-latest")
        self.assertEqual(body["max_tokens"], 600)
        self.assertEqual(body["reasoning_effort"], "none")
        self.assertEqual(
            [item["role"] for item in body["messages"]],
            [
                "system",
                "assistant",
                "user",
            ],
        )

    async def test_content_blocks_are_supported(self) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": [{"text": "one"}, {"text": " two"}]}}
                    ]
                },
            )
        )
        client = MistralClient(settings(), transport=transport, max_attempts=1)
        try:
            answer = await client.chat(
                system_prompt="system", history=[], user_text="hello"
            )
        finally:
            await client.close()
        self.assertEqual(answer, "one two")

    async def test_http_error_is_sanitized(self) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                401,
                json={"message": "secret upstream detail"},
            )
        )
        client = MistralClient(settings(), transport=transport, max_attempts=1)
        try:
            with self.assertRaises(MistralAPIError) as raised:
                await client.chat(system_prompt="system", history=[], user_text="hello")
        finally:
            await client.close()

        self.assertEqual(raised.exception.status_code, 401)
        self.assertNotIn("secret upstream detail", str(raised.exception))

    async def test_empty_response_is_rejected(self) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"choices": [{"message": {"content": ""}}]},
            )
        )
        client = MistralClient(settings(), transport=transport, max_attempts=1)
        try:
            with self.assertRaisesRegex(MistralAPIError, "пустой ответ"):
                await client.chat(system_prompt="system", history=[], user_text="hello")
        finally:
            await client.close()


if __name__ == "__main__":
    unittest.main()
