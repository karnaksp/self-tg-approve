"""
Модуль содержит обработчики действий в боте.
"""

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

import variables_conf
from commands import logger
from utils import (
    approve_user,
    process_user_message,
    reject_user,
    send_chunked_response,
    send_photo_to_admin,
    waiting_message_check,
)


async def handle_sticker(update: Update, context):
    """
    Обрабатывает стикер, отправленный администратором.

    Если стикер отправлен не администратором, или стикер отправлен без запроса,
    пользователю будет отправлено предупреждение.
    Если стикер отправлен не администратором, функция не будет выполнять
    никаких действий.
    """
    message = update.message
    user_id = message.from_user.id
    chat_username = message.chat.username

    if user_id != variables_conf.ADMIN_ID:
        return

    if not variables_conf.STIKCER_EXPECTED_FLG:
        await message.reply_text("Пожалуйста, сначала отправьте команду /sendsticker.")
        logger.warning(
            f"Пользователь {chat_username} попытался отправить стикер без запроса."
        )
        return

    if not message.sticker:
        await message.reply_text("Это не стикер! Пожалуйста, отправьте именно стикер.")
        logger.warning(f"Пользователь {chat_username} отправил не стикер.")
        return

    sticker_id = message.sticker.file_id
    logger.info(f"Получен стикер ID: {sticker_id} от пользователя {chat_username}")
    await context.bot.send_sticker(variables_conf.CHANNEL_ID, sticker_id)
    logger.info(
        f"Стикер от {chat_username} отправлен в канал {variables_conf.CHANNEL_ID}"
    )
    variables_conf.STIKCER_EXPECTED_FLG = False


async def handle_non_photo_message(update: Update, user_name: str):
    """Обрабатывает сообщения, если пользователь отправил не фото."""
    await update.message.reply_text("Это не мем!!!! (╬ಠ益ಠ)\n\nМне нужна картинка!")
    logger.warning(
        f"Пользователь {user_name} отправил не фото, а написал: '{update.message.text}'"
    )


async def handle_unexpected_request(update: Update):
    """Обрабатывает сообщения, когда ожидание фото отключено."""
    await update.message.reply_text(
        "Не пойму, шо ты хочешь, дорогой! Выбери команду..."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает сообщения от пользователей.
    Если ожидается фото, отправляет его администратору."""
    message = update.message
    user_id = message.from_user.id
    user_name = message.chat.username

    if variables_conf.PHOTO_EXPECTED_FLG:
        if message.photo:
            photo_id = message.photo[-1].file_id
            await send_photo_to_admin(context, photo_id, user_name, user_id)
            variables_conf.PHOTO_EXPECTED_FLG = False
        else:
            await handle_non_photo_message(update, user_name)
    else:
        await handle_unexpected_request(update)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает callback запросы (нажатие на кнопки)

    Если callback_query содержит "approve", то функция вызывает approve_user
    Если callback_query содержит "reject", то функция вызывает reject_user
    """
    query = update.callback_query
    await query.answer()

    user_id = query.data.split("_")[1]
    user = await context.bot.get_chat(user_id)
    user_name = user.username

    if "approve" in query.data:
        logger.info(f"Обрабатывается одобрение запроса пользователя {user_name}")
        await approve_user(context, user_id, user_name, query)
    else:
        logger.info(f"Обрабатывается отказ в запросе пользователя {user_name}")
        await reject_user(context, user_id, user_name, query)


async def handle_talk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает сообщения от пользователей, когда они находитятся в режиме разговора.
    """
    if context.user_data.get("in_talk"):
        asyncio.create_task(waiting_message_check(update, context))
        full_response = await process_user_message(update, context)
        await send_chunked_response(update, full_response)
    else:
        await update.message.reply_text(
            "Ты не в режиме общения. Чтобы пообщаться с Ck, используй команду /talk."
        )
