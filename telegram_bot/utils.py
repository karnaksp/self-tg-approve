"""
Модуль дополнительнхы инструментов.
"""

import asyncio
import json
import os
import random
import re
from datetime import datetime, timedelta
from typing import Dict, Optional

import requests
from ollama import AsyncClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import variables_conf
from commands import logger
from message_config import WAITING_PHRASES

ollama_base_url = os.getenv("OLLAMA_BASE_URL")
client = AsyncClient(host=ollama_base_url)


async def llama_chat(
    user_message: str, history: str, use_rag: bool = False
) -> Dict[str, Optional[str]]:
    """
    Отправьте сообщение чат-боту Llama и получает его ответ.

    Сообщение отправляется в API Ollama, а ответ представляет собой либо строку,
    содержащую ответ чат-бота (если use_rag=False), либо объект JSON,
    содержащий ответ чат-бота (если use_rag=True).
    """
    url = "http://api:8504/query"
    params = {"text": user_message, "history": history, "rag": use_rag}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()

        # if use_rag:
        #     result = "".join(
        #         json.loads(line.decode("utf-8").strip()[len("data:") :].strip()).get(
        #             "variables_conf.TOKEN", ""
        #         )
        #         for line in response.iter_lines()
        #         if line
        #     )
        #     return {"result": result}
        return response.json().get("result")
    except (requests.exceptions.HTTPError, requests.exceptions.RequestException) as err:
        logger.error(f"Request error occurred: {err}")
        return f"Черт. Ты меня положил..."
    except ValueError as json_err:
        logger.error(f"JSON decode error: {json_err}")
        return {"error": "Failed to decode JSON from response."}


async def send_chunked_response(
    update: Update, full_response: str, chunk_size: int = 50
) -> None:
    """Разбивает длинный ответ на части и отправляет их пользователю."""
    if not isinstance(full_response, str):
        if isinstance(full_response, dict):
            full_response = str(full_response)
        else:
            logger.error("Неправильный формат данных. Ожидалась строка.")
    non_think_response = full_response.split("</think>")[-1]
    words = non_think_response.split()
    message_parts = []
    chunk = []
    total_words = 0

    for word in words:
        chunk.append(word)
        total_words += 1
        if total_words >= chunk_size and re.search(r"[.!?]", word):
            message_parts.append(" ".join(chunk))
            chunk = []
            total_words = 0
    if chunk:
        message_parts.append(" ".join(chunk))

    for part in message_parts:
        await update.message.reply_text(part)
        await asyncio.sleep(1)


async def process_user_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> str:
    """Обрабатывает сообщение пользователя и возвращает ответ."""
    user_name = update.message.chat.username
    text = update.message.text
    context.user_data["last_message_time"] = datetime.now()
    logger.info(f"Пользователь {user_name} прислал сообщение для разговора: '{text}'")
    full_response = await llama_chat(
        text, "", use_rag=context.user_data.get("use_rag", False)
    )
    logger.info(f"Ответ от ассистента: {full_response}")

    return full_response


async def waiting_message_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Проверяет, было ли последнее сообщение отправлено более 40 секунд назад,
    и отправьте ожидающее сообщение, если это так.
    """
    last_message_time = context.user_data.get("last_message_time")
    if last_message_time and datetime.now() - last_message_time >= timedelta(
        seconds=40
    ):
        waiting_message = random.choice(WAITING_PHRASES)
        await update.message.reply_text(waiting_message)


async def send_photo_to_admin(
    context: ContextTypes.DEFAULT_TYPE, photo_id: str, user_name: str, user_id: int
):
    """Отправляет фото администратору с кнопками для одобрения или отказа."""
    keyboard = [
        [InlineKeyboardButton("Одобрить", callback_data=f"approve_{user_id}")],
        [InlineKeyboardButton("Отказать", callback_data=f"reject_{user_id}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_photo(
        variables_conf.ADMIN_ID,
        photo_id,
        caption=f"Запрос от пользователя {user_name}",
        reply_markup=reply_markup,
    )
    logger.info(f"Фото от {user_name} отправлено администратору")


async def approve_user(
    context: ContextTypes.DEFAULT_TYPE, user_id: str, user_name: str, query
):
    """Обрабатывает одобрение пользователя."""
    try:
        invite_link = await context.bot.create_chat_invite_link(
            variables_conf.CHANNEL_ID
        )
        await context.bot.send_message(
            user_id,
            f"Было смешно (или возбуждающе). Проходи по ссылке!: {invite_link.invite_link}",
        )
        await query.message.reply_text(f"Пользователь {user_name} одобрен!")
        logger.info(f"Пользователь {user_name} одобрен для вступления в канал")
    except Exception as e:
        await query.message.reply_text(f"Ошибка при одобрении: {e}")
        logger.error(f"Ошибка при одобрении пользователя {user_name}: {e}")


async def reject_user(
    context: ContextTypes.DEFAULT_TYPE, user_id: str, user_name: str, query
):
    """Обрабатывает отказ пользователю."""
    try:
        await context.bot.send_message(user_id, "Твой мем не смешной! (¬_¬ )")
        logger.info(f"Пользователю {user_name} отправлено сообщение об отказе")
    except Exception as e:
        await query.message.reply_text(f"Ошибка при отказе: {e}")
        logger.error(f"Ошибка при отказе пользователя {user_name}: {e}")


# async def upload_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     user_name = update.message.chat.username
#     logger.info(f"Пользователь {user_name} загрузил PDF документ")
#     file = await context.bot.get_file(update.message.document.file_id)
#     with tempfile.NamedTemporaryFile(delete=True) as temp:
#         await file.download_to_drive(temp.name)
#         # Here you can add code to process the PDF document using your API
# await update.message.reply_text("PDF документ успешно загружен и
# обработан.")
