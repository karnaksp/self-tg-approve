"""Validate Telegram credentials and channel permissions without polling."""

from __future__ import annotations

import asyncio

from dotenv import load_dotenv
from telegram import Bot

from .config import Settings


async def check() -> None:
    load_dotenv(override=False)
    settings = Settings.from_env()
    async with Bot(settings.telegram_token) as bot:
        me = await bot.get_me()
        channel = await bot.get_chat(settings.channel_id)
        membership = await bot.get_chat_member(settings.channel_id, me.id)
    can_invite = bool(getattr(membership, "can_invite_users", False))
    print(
        f"Telegram OK (@{me.username}): channel={channel.title!r}, "
        f"status={membership.status}, can_invite_users={can_invite}"
    )


if __name__ == "__main__":
    asyncio.run(check())
