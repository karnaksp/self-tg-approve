"""
Модуль, содержащий команды бота.
"""

import random
from datetime import datetime

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

import variables_conf
from logger_config import setup_logger
from message_config import COFFEE_OPTIONS, INFO_MESSAGE

logger = setup_logger()


async def start(update: Update, context):
    """
    Команда /start
    """
    message = "Доброе утро, солнышко! Присаживайся, выбирай команду."
    await update.message.reply_text(message)
    logger.info(
        f"Пользователю {update.message.from_user.username} отправлено приветственное"
    )


async def send_sticker_request(update: Update, context):
    """
    Устанавливает флаг ожидания стикера и отправляет пользователю запрос на отправку стикера.
    """

    variables_conf.STIKCER_EXPECTED_FLG = True
    await update.message.reply_text("Пожалуйста, отправьте стикер.")
    logger.info(f"Запрос на стикер от пользователя {update.message.from_user.username}")


async def get_channel_info(context):
    """
    Получает информацию о канале, в котором работает бот.
    """
    try:
        chat = await context.bot.get_chat(variables_conf.CHANNEL_ID)
        logger.info(f"Веду работу в канале: {chat.title}")
    except TelegramError as e:
        logger.error(f"Ошибка при получении информации о канале: {e}")


async def join_request(update: Update, context):
    """
    Команда /join_request
    """

    variables_conf.PHOTO_EXPECTED_FLG = True
    await get_channel_info(context)
    await update.message.reply_text(
        "Здравствуй, милый! За вход надо платить: отправь мне смешной мем, чтобы пройти (картинку)."
    )
    logger.info(
        f"Пользователю {update.message.from_user.username} отправлено приветственное сообщение"
    )


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /info
    Отправляет пользователю инструкцию по получению доступа к каналу.
    """
    await update.message.reply_text(INFO_MESSAGE)
    logger.info(
        f"Пользователю {update.message.from_user.username} отправлено сообщение с инструкцией доступа"
    )


async def coffee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /coffee
    Отправляет пользователю случайную YouTube ссылку.
    """
    selected_media = random.choice(COFFEE_OPTIONS)
    await context.bot.send_message(update.message.chat_id, selected_media)
    logger.info(
        f"Пользователю {update.message.from_user.username} отправлена YouTube ссылка: {selected_media}"
    )


async def start_talk(update: Update, context: ContextTypes.DEFAULT_TYPE, use_rag=False):
    """
    Команда /talk
    Начинает диалог с ботом. Если use_rag=True, то бот будет
    сохранять историю диалога в базе даннных.
    """
    user_name = update.message.chat.username
    logger.info(f"Пользователь {user_name} начал диалог через /talk")
    await update.message.reply_text(
        "Приветики! Внимательно слушаю тебя, ебало ослиное."
    )
    context.user_data["in_talk"] = True
    context.user_data["last_message_time"] = datetime.now()
    context.user_data["message_history"] = []
    context.user_data["use_rag"] = use_rag


async def stop_talk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /stop_talk
    Завершает диалог с ботом.

    """

    user_name = update.message.chat.username
    logger.info(f"Пользователь {user_name} завершил диалог через /stop_talk")
    await update.message.reply_text("Пока-пока ^-^.")
    context.user_data["in_talk"] = False
    context.user_data["last_message_time"] = datetime.now()
    context.user_data["message_history"] = []
