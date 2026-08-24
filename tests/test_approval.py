from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from self_tg_approve.app import handle_approval_callback
from self_tg_approve.config import Settings


def settings() -> Settings:
    return Settings(
        telegram_token="telegram-secret",
        channel_id=-100123,
        admin_id=42,
        mistral_api_key="mistral-secret",
    )


def callback_fixture(actor_id: int = 42):
    message = SimpleNamespace(
        chat_id=42,
        message_id=99,
        reply_text=AsyncMock(),
    )
    query = SimpleNamespace(
        data="approve:777",
        message=message,
        answer=AsyncMock(),
        edit_message_reply_markup=AsyncMock(),
    )
    update = SimpleNamespace(
        callback_query=query,
        effective_user=SimpleNamespace(id=actor_id),
    )
    bot = SimpleNamespace(
        create_chat_invite_link=AsyncMock(
            return_value=SimpleNamespace(invite_link="https://t.me/+one-use")
        ),
        send_message=AsyncMock(),
    )
    application = SimpleNamespace(bot_data={"settings": settings()})
    context = SimpleNamespace(application=application, bot=bot)
    return update, context, query, bot, message


class ApprovalTests(unittest.IsolatedAsyncioTestCase):
    async def test_non_admin_cannot_process_callback(self) -> None:
        update, context, query, bot, _ = callback_fixture(actor_id=7)

        await handle_approval_callback(update, context)

        query.answer.assert_awaited_once_with(
            "Эта кнопка доступна только администратору.", show_alert=True
        )
        bot.create_chat_invite_link.assert_not_awaited()
        bot.send_message.assert_not_awaited()

    async def test_approval_creates_one_use_expiring_link_once(self) -> None:
        update, context, query, bot, message = callback_fixture()

        await handle_approval_callback(update, context)
        await handle_approval_callback(update, context)

        bot.create_chat_invite_link.assert_awaited_once()
        kwargs = bot.create_chat_invite_link.await_args.kwargs
        self.assertEqual(kwargs["member_limit"], 1)
        self.assertEqual(kwargs["chat_id"], -100123)
        bot.send_message.assert_awaited_once()
        query.edit_message_reply_markup.assert_awaited_once_with(reply_markup=None)
        self.assertEqual(message.reply_text.await_count, 2)


if __name__ == "__main__":
    unittest.main()
