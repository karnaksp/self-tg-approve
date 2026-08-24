"""Perform one explicit live Mistral request using the local environment."""

from __future__ import annotations

import asyncio

from dotenv import load_dotenv

from .config import Settings
from .mistral import MistralClient


async def check() -> None:
    load_dotenv(override=False)
    settings = Settings.from_env()
    client = MistralClient(settings)
    try:
        answer = await client.chat(
            system_prompt="Ответь кратко и без пояснений.",
            history=[],
            user_text="Ответь одним словом: готова",
        )
    finally:
        await client.close()
    print(f"Mistral OK ({settings.mistral_model}): {answer[:120]}")


if __name__ == "__main__":
    asyncio.run(check())
