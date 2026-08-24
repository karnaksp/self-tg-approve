"""Telegram handlers and application lifecycle."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import random
import time
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from dotenv import load_dotenv
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ChatType
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from . import __version__
from .config import ConfigError, Settings
from .memory import (
    ChatMessage,
    append_exchange,
    clear_expired_history,
    split_telegram_text,
)
from .mistral import MistralAPIError, MistralClient
from .prompts import (
    APPROVAL_TEXT,
    BOT_COMMANDS,
    BOT_DESCRIPTION,
    BOT_SHORT_DESCRIPTION,
    COFFEE_OPTIONS,
    INFO_TEXT,
    JOIN_REQUEST_TEXT,
    MISTRAL_FAILURE_TEXT,
    NON_PHOTO_TEXT,
    NOT_A_STICKER_TEXT,
    REJECTION_TEXT,
    SEND_STICKER_REQUEST_TEXT,
    START_TEXT,
    STICKER_WITHOUT_REQUEST_TEXT,
    SYSTEM_PROMPT,
    TALK_INACTIVE_TEXT,
    TALK_START_TEXT,
    TALK_STOP_TEXT,
    UNEXPECTED_TEXT,
    WAITING_PHRASES,
)

LOGGER = logging.getLogger(__name__)
CALLBACK_PATTERN = r"^(approve|reject):[0-9]+$"
SENSITIVE_NETWORK_LOGGERS = ("httpx", "httpcore", "telegram.request")


def _settings(context: CallbackContext[Any, Any, Any, Any]) -> Settings:
    return cast(Settings, context.application.bot_data["settings"])


def _mistral(context: CallbackContext[Any, Any, Any, Any]) -> MistralClient:
    return cast(MistralClient, context.application.bot_data["mistral"])


def _private_chat(update: Update) -> bool:
    return bool(
        update.effective_chat and update.effective_chat.type == ChatType.PRIVATE
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(START_TEXT)


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(INFO_TEXT)


async def coffee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(random.choice(COFFEE_OPTIONS))


async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return
    if not _private_chat(update):
        await message.reply_text("Открой личный чат со мной и повтори /join_request.")
        return
    context.user_data.pop("awaiting_sticker", None)
    context.user_data["awaiting_photo"] = True
    await message.reply_text(JOIN_REQUEST_TEXT)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user or not message.photo:
        return
    settings = _settings(context)
    if user.id == settings.admin_id and context.user_data.get("awaiting_sticker"):
        await message.reply_text(NOT_A_STICKER_TEXT)
        return
    if not context.user_data.get("awaiting_photo"):
        await message.reply_text(UNEXPECTED_TEXT)
        return

    display_name = user.username or user.full_name
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Одобрить", callback_data=f"approve:{user.id}")],
            [InlineKeyboardButton("Отказать", callback_data=f"reject:{user.id}")],
        ]
    )
    try:
        await context.bot.send_photo(
            chat_id=settings.admin_id,
            photo=message.photo[-1].file_id,
            caption=f"Запрос от пользователя {display_name}",
            reply_markup=keyboard,
        )
    except TelegramError:
        LOGGER.exception("Не удалось передать заявку пользователя %s", user.id)
        await message.reply_text(
            "Не удалось передать заявку администратору. Попробуй ещё раз чуть позже."
        )
        return

    context.user_data["awaiting_photo"] = False


async def handle_approval_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    actor = update.effective_user
    if not query or not actor or not query.data:
        return

    settings = _settings(context)
    if actor.id != settings.admin_id:
        await query.answer(
            "Эта кнопка доступна только администратору.", show_alert=True
        )
        return

    await query.answer()
    action, raw_user_id = query.data.split(":", 1)
    user_id = int(raw_user_id)
    message = query.message
    if message is None:
        return

    processed = context.application.bot_data.setdefault("processed_requests", set())
    request_key = (message.chat_id, message.message_id)
    if request_key in processed:
        await message.reply_text("Эта заявка уже обработана.")
        return

    try:
        user_chat = await context.bot.get_chat(user_id)
        user_name = (
            getattr(user_chat, "username", None)
            or getattr(user_chat, "full_name", None)
            or str(user_id)
        )
    except TelegramError:
        user_name = str(user_id)

    try:
        if action == "approve":
            expires_at = datetime.now(UTC) + timedelta(
                hours=settings.invite_link_ttl_hours
            )
            invite = await context.bot.create_chat_invite_link(
                chat_id=settings.channel_id,
                expire_date=expires_at,
                member_limit=1,
                name=f"approval-{user_id}",
            )
            await context.bot.send_message(
                chat_id=user_id,
                text=APPROVAL_TEXT.format(invite_link=invite.invite_link),
            )
            result_text: str | None = f"Пользователь {user_name} одобрен!"
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=REJECTION_TEXT,
            )
            result_text = None

        processed.add(request_key)
        if len(processed) > 1_000:
            processed.clear()
            processed.add(request_key)
        await query.edit_message_reply_markup(reply_markup=None)
        if result_text is not None:
            await message.reply_text(result_text)
    except TelegramError:
        LOGGER.exception("Ошибка обработки заявки пользователя %s", user_id)
        operation = "одобрении" if action == "approve" else "отказе"
        await message.reply_text(
            f"Ошибка при {operation}: не удалось обработать заявку."
        )


async def send_sticker_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return
    if user.id != _settings(context).admin_id:
        await message.reply_text("Команда доступна только администратору.")
        return
    context.user_data.pop("awaiting_photo", None)
    context.user_data["awaiting_sticker"] = True
    await message.reply_text(SEND_STICKER_REQUEST_TEXT)


async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user or not message.sticker:
        return
    settings = _settings(context)
    if user.id != settings.admin_id:
        return
    if not context.user_data.get("awaiting_sticker"):
        await message.reply_text(STICKER_WITHOUT_REQUEST_TEXT)
        return
    try:
        await context.bot.send_sticker(settings.channel_id, message.sticker.file_id)
    except TelegramError:
        LOGGER.exception("Не удалось отправить стикер в канал")
        await message.reply_text("Не удалось опубликовать стикер. Проверь права бота.")
        return
    context.user_data["awaiting_sticker"] = False


async def start_talk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return
    if not _private_chat(update):
        await message.reply_text("Разговор с агентессой доступен в личном чате.")
        return
    settings = _settings(context)
    allowed = settings.mistral_allowed_user_ids
    if allowed and user.id not in allowed and user.id != settings.admin_id:
        await message.reply_text("Разговор с агентессой для этого аккаунта отключён.")
        return
    context.user_data["talk_active"] = True
    context.user_data["mistral_history"] = []
    context.user_data["last_activity"] = datetime.now(UTC)
    await message.reply_text(TALK_START_TEXT)


async def clear_talk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        context.user_data["mistral_history"] = []
        context.user_data["last_activity"] = datetime.now(UTC)
        await update.effective_message.reply_text("Контекст текущей сессии очищен.")


async def stop_talk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        context.user_data["talk_active"] = False
        context.user_data["mistral_history"] = []
        context.user_data.pop("last_activity", None)
        await update.effective_message.reply_text(TALK_STOP_TEXT)


def _mistral_error_text(error: MistralAPIError) -> str:
    return MISTRAL_FAILURE_TEXT


async def _send_waiting_phrase(message: Any) -> None:
    await asyncio.sleep(40)
    await message.reply_text(random.choice(WAITING_PHRASES))


async def handle_talk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user or not message.text:
        return
    settings = _settings(context)
    if not context.user_data.get("talk_active"):
        if user.id == settings.admin_id and context.user_data.get("awaiting_sticker"):
            await message.reply_text(NOT_A_STICKER_TEXT)
            return
        if context.user_data.get("awaiting_photo"):
            await message.reply_text(NON_PHOTO_TEXT)
            return
        await message.reply_text(TALK_INACTIVE_TEXT)
        return

    now = datetime.now(UTC)
    expired_now = clear_expired_history(
        context.user_data,
        now,
        settings.session_ttl_minutes,
    )
    expired_notice = bool(context.user_data.pop("session_expired_notice", False))
    expired = expired_now or expired_notice
    if expired:
        context.user_data["mistral_history"] = []
        await message.reply_text("Старая сессия истекла — начинаем с чистого листа.")

    monotonic_now = time.monotonic()
    last_request = context.user_data.get("last_request_monotonic")
    if isinstance(last_request, (int, float)):
        remaining = settings.request_cooldown_seconds - (monotonic_now - last_request)
        if remaining > 0:
            await message.reply_text(
                f"Дай мне ещё {remaining:.1f} сек. и повтори сообщение."
            )
            return
    context.user_data["last_request_monotonic"] = monotonic_now

    user_text = message.text.strip()
    if len(user_text) > 4_000:
        user_text = user_text[:4_000]
        await message.reply_text("Сообщение длинное — возьму первые 4000 символов.")

    raw_history = context.user_data.get("mistral_history", [])
    history = cast(
        list[ChatMessage], raw_history if isinstance(raw_history, list) else []
    )
    context.user_data["last_activity"] = now
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    waiting_task = asyncio.create_task(_send_waiting_phrase(message))
    try:
        answer = await _mistral(context).chat(
            system_prompt=SYSTEM_PROMPT,
            history=history,
            user_text=user_text,
        )
    except MistralAPIError as exc:
        LOGGER.warning(
            "Mistral request failed for user %s: status=%s",
            user.id,
            exc.status_code,
        )
        await message.reply_text(_mistral_error_text(exc))
        return
    finally:
        waiting_task.cancel()
        with contextlib.suppress(asyncio.CancelledError, TelegramError):
            await waiting_task

    context.user_data["mistral_history"] = append_exchange(
        history,
        user_text,
        answer,
        max_messages=settings.session_history_messages,
        max_chars=settings.session_history_chars,
    )
    context.user_data["last_activity"] = datetime.now(UTC)
    for chunk in split_telegram_text(answer):
        await message.reply_text(chunk)


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return
    if context.user_data.get("talk_active"):
        await handle_talk(update, context)
    else:
        await update.effective_message.reply_text(TALK_INACTIVE_TEXT)


async def handle_other_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return
    settings = _settings(context)
    if user.id == settings.admin_id and context.user_data.get("awaiting_sticker"):
        await message.reply_text(NOT_A_STICKER_TEXT)
    elif context.user_data.get("awaiting_photo"):
        await message.reply_text(NON_PHOTO_TEXT)
    else:
        await message.reply_text(UNEXPECTED_TEXT)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user or user.id != _settings(context).admin_id:
        return
    settings = _settings(context)
    await message.reply_text(
        f"self-tg-approve v{__version__}\nMistral model: {settings.mistral_model}\nMode: polling"
    )


async def post_init(application: Application[Any, Any, Any, Any, Any, Any]) -> None:
    commands = [
        BotCommand(command, description) for command, description in BOT_COMMANDS
    ]
    await application.bot.set_my_commands(commands)
    await application.bot.set_my_description(description=BOT_DESCRIPTION)
    await application.bot.set_my_short_description(
        short_description=BOT_SHORT_DESCRIPTION
    )
    me = await application.bot.get_me()
    LOGGER.info("Бот @%s запущен, версия %s", me.username, __version__)
    application.bot_data["session_cleanup_task"] = asyncio.create_task(
        _session_cleanup_loop(application),
        name="session-cleanup",
    )


async def _session_cleanup_loop(
    application: Application[Any, Any, Any, Any, Any, Any],
) -> None:
    settings = cast(Settings, application.bot_data["settings"])
    while True:
        await asyncio.sleep(300)
        now = datetime.now(UTC)
        cleared = sum(
            clear_expired_history(state, now, settings.session_ttl_minutes)
            for state in application.user_data.values()
        )
        if cleared:
            LOGGER.info("Очищено просроченных Mistral-сессий: %s", cleared)


async def post_shutdown(application: Application[Any, Any, Any, Any, Any, Any]) -> None:
    cleanup_task = application.bot_data.get("session_cleanup_task")
    if isinstance(cleanup_task, asyncio.Task):
        cleanup_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await cleanup_task
    client = cast(MistralClient, application.bot_data["mistral"])
    await client.close()


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    error = context.error
    if error is None:
        LOGGER.error("Необработанная ошибка Telegram update без exception")
        return
    LOGGER.error(
        "Необработанная ошибка Telegram update",
        exc_info=(type(error), error, error.__traceback__),
    )


def build_application(
    settings: Settings,
    *,
    mistral_client: MistralClient | None = None,
) -> Application[Any, Any, Any, Any, Any, Any]:
    application = (
        ApplicationBuilder()
        .token(settings.telegram_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    application.bot_data["settings"] = settings
    application.bot_data["mistral"] = mistral_client or MistralClient(settings)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("join_request", join_request))
    application.add_handler(CommandHandler("coffee", coffee))
    application.add_handler(CommandHandler("sendsticker", send_sticker_request))
    application.add_handler(CommandHandler("talk", start_talk))
    application.add_handler(CommandHandler("clear", clear_talk))
    application.add_handler(CommandHandler("stop_talk", stop_talk))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(
        CallbackQueryHandler(handle_approval_callback, pattern=CALLBACK_PATTERN)
    )
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_talk)
    )
    application.add_handler(
        MessageHandler(filters.ALL & ~filters.COMMAND, handle_other_message)
    )
    application.add_error_handler(error_handler)
    return application


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # Telegram embeds the bot token in its Bot API URL. Never allow HTTP access
    # loggers to print full request URLs, even when application DEBUG is enabled.
    for logger_name in SENSITIVE_NETWORK_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def main() -> None:
    load_dotenv(override=False)
    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        raise SystemExit(f"Ошибка конфигурации: {exc}") from exc

    configure_logging(settings.log_level)
    application = build_application(settings)
    application.run_polling(drop_pending_updates=False)
