"""Validate Telegram credentials and channel permissions without polling."""

from __future__ import annotations

import asyncio

from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

from .config import ConfigError, Settings


async def check() -> None:
    load_dotenv(override=False)
    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        print(f"ОШИБКА КОНФИГУРАЦИИ: {exc}")
        return

    async with Bot(settings.telegram_token) as bot:
        me = await bot.get_me()
        if settings.admin_id == me.id:
            print(
                f"ОШИБКА: ADMIN_ID ({settings.admin_id}) совпадает с ID бота (@{me.username})!\n"
                "Бот не может отправлять сообщения самому себе.\n"
                "Укажите в .env ваш личный Telegram ID (узнать его можно у @userinfobot)."
            )
            return

        channel = await bot.get_chat(settings.channel_id)
        membership = await bot.get_chat_member(settings.channel_id, me.id)
        can_invite = bool(getattr(membership, "can_invite_users", False))
        print(
            f"Telegram OK (@{me.username}): channel={channel.title!r}, "
            f"status={membership.status}, can_invite_users={can_invite}"
        )

        try:
            admin_chat = await bot.get_chat(settings.admin_id)
            admin_name = (
                getattr(admin_chat, "username", None)
                or getattr(admin_chat, "full_name", None)
                or str(admin_chat.id)
            )
            print(f"Admin OK: {admin_name} (id={settings.admin_id})")
        except TelegramError as exc:
            print(
                f"ВНИМАНИЕ: Бот не смог получить чат с администратором (id={settings.admin_id}): {exc}\n"
                "Убедитесь, что администратор запустил бота (нажал /start в личных сообщениях с ботом)!"
            )


if __name__ == "__main__":
    asyncio.run(check())
