from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from telegram.constants import ChatType

from self_tg_approve.app import (
    handle_photo,
    handle_talk,
    join_request,
    send_sticker_request,
    start_talk,
    stop_talk,
)
from self_tg_approve.config import Settings


def settings() -> Settings:
    return Settings(
        telegram_token="telegram-secret",
        channel_id=-100123,
        admin_id=42,
        mistral_api_key="mistral-secret",
    )


def context(*, user_data: dict | None = None):
    bot = SimpleNamespace(
        send_photo=AsyncMock(),
        send_chat_action=AsyncMock(),
    )
    return SimpleNamespace(
        user_data={} if user_data is None else user_data,
        application=SimpleNamespace(bot_data={"settings": settings()}),
        bot=bot,
    )


def update(*, user_id: int = 7, username: str = "visitor", text: str | None = None):
    message = SimpleNamespace(
        text=text,
        photo=None,
        reply_text=AsyncMock(),
    )
    user = SimpleNamespace(id=user_id, username=username, full_name="Visitor")
    return (
        SimpleNamespace(
            effective_message=message,
            effective_user=user,
            effective_chat=SimpleNamespace(id=user_id, type=ChatType.PRIVATE),
        ),
        message,
    )


class LegacyHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_join_request_and_non_photo_use_legacy_copy(self) -> None:
        event, message = update(text="/join_request")
        bot_context = context()

        await join_request(event, bot_context)
        await handle_talk(event, bot_context)

        self.assertEqual(
            [call.args[0] for call in message.reply_text.await_args_list],
            [
                "Здравствуй, милый! За вход надо платить: отправь мне смешной "
                "мем, чтобы пройти (картинку).",
                "Это не мем!!!! (╬ಠ益ಠ)\n\nМне нужна картинка!",
            ],
        )

    async def test_talk_start_inactive_and_stop_use_legacy_copy(self) -> None:
        event, message = update(text="привет")
        bot_context = context()

        await handle_talk(event, bot_context)
        await start_talk(event, bot_context)
        await stop_talk(event, bot_context)

        self.assertEqual(
            [call.args[0] for call in message.reply_text.await_args_list],
            [
                "Ты не в режиме общения. Чтобы пообщаться с Ck, используй "
                "команду /talk.",
                "Приветики! Внимательно слушаю тебя, ебало ослиное.",
                "Пока-пока ^-^.",
            ],
        )

    async def test_photo_uses_old_caption_buttons_and_no_new_ack(self) -> None:
        event, message = update()
        message.photo = [SimpleNamespace(file_id="photo-id")]
        bot_context = context(user_data={"awaiting_photo": True})

        await handle_photo(event, bot_context)

        bot_context.bot.send_photo.assert_awaited_once()
        kwargs = bot_context.bot.send_photo.await_args.kwargs
        self.assertEqual(kwargs["caption"], "Запрос от пользователя visitor")
        keyboard = kwargs["reply_markup"].inline_keyboard
        self.assertEqual(
            [[button.text for button in row] for row in keyboard],
            [["Одобрить"], ["Отказать"]],
        )
        message.reply_text.assert_not_awaited()
        self.assertFalse(bot_context.user_data["awaiting_photo"])

    async def test_send_sticker_prompt_is_legacy_copy(self) -> None:
        event, message = update(user_id=42)
        bot_context = context()

        await send_sticker_request(event, bot_context)

        message.reply_text.assert_awaited_once_with("Пожалуйста, отправьте стикер.")
        self.assertTrue(bot_context.user_data["awaiting_sticker"])


if __name__ == "__main__":
    unittest.main()
