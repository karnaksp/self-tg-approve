"""
Модуль содержит обработчики действий в боте.
"""

import asyncio
import sys

from graph_ticker.main import main
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

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


(
    ASK_TICKERS,
    ASK_START_DATE,
    ASK_END_DATE,
    ASK_WITH_INVESTMENTS,
    ASK_USE_GRADIENT,
    ASK_INITIAL_INVESTMENT,
    ASK_MONTHLY_INVESTMENT,
    ASK_YEARLY_INVESTMENT,
    ASK_VALUE_COL,
    ASK_DURATION,
    ASK_FPS,
    ASK_NO_LEGEND,
    ASK_CURRENCY,
    ASK_TITLE,
    ASK_UNDER_TITLE,
    CONFIRM_RUN,
) = range(16)


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


async def create_graph_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != variables_conf.ADMIN_ID:
        await update.message.reply_text("Эта команда доступна только админу.")
        return ConversationHandler.END

    context.user_data["video_params"] = {}
    await update.message.reply_text(
        "Запускаем создание видео!\n"
        "Введите тикеры через | (например AAPL:MOEX:USD,GOOG:MOEX:USD) или оставьте пустым для пропуска:"
    )
    return ASK_TICKERS


async def ask_tickers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text:
        context.user_data["video_params"]["tickers"] = [
            t.strip() for t in text.split(",")
        ]
    else:
        context.user_data["video_params"]["tickers"] = []
    await update.message.reply_text(
        "Введите параметры тикера: AAPL|global|shares для yafinance или SBER|stock|shares для moex"
    )
    return ASK_START_DATE


async def ask_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text:
        context.user_data["video_params"]["start_date"] = text
    else:
        context.user_data["video_params"]["start_date"] = None
    await update.message.reply_text("Введите дату начала (YYYY-MM-DD)")
    return ASK_END_DATE


async def ask_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text:
        context.user_data["video_params"]["end_date"] = text
    else:
        context.user_data["video_params"]["end_date"] = None
    await update.message.reply_text("Введите дату конца (YYYY-MM-DD)")
    return ASK_WITH_INVESTMENTS


async def ask_with_investments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    context.user_data["video_params"]["with_investments"] = text.startswith(
        "д"
    ) or text.startswith("y")
    await update.message.reply_text("Использовать инвестиции? (да/нет)")
    return ASK_USE_GRADIENT


async def ask_use_gradient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    context.user_data["video_params"]["use_gradient"] = text.startswith(
        "д"
    ) or text.startswith("y")
    await update.message.reply_text("Использовать градиент? (да/нет)")
    return ASK_INITIAL_INVESTMENT


async def ask_initial_investment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["video_params"]["initial_investment"] = (
        int(text) if text.isdigit() else 10000
    )
    await update.message.reply_text(
        "Введите начальную инвестицию (целое число) или оставьте пустым:"
    )
    return ASK_MONTHLY_INVESTMENT


async def ask_monthly_investment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["video_params"]["monthly_investment"] = (
        int(text) if text.isdigit() else 0
    )
    await update.message.reply_text(
        "Введите ежемесячную инвестицию (целое число) или оставьте пустым:"
    )
    return ASK_YEARLY_INVESTMENT


async def ask_yearly_investment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["video_params"]["yearly_investment"] = (
        int(text) if text.isdigit() else 0
    )
    await update.message.reply_text(
        "Введите ежемесячную инвестицию (целое число) или оставьте пустым:"
    )
    return ASK_VALUE_COL


async def ask_value_col(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["video_params"]["value_col"] = (
        text if text else "CAPITAL_REINVEST"
    )
    await update.message.reply_text(
        "Введите название колонки с капиталом или оставьте пустым:"
    )
    return ASK_DURATION


async def ask_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["video_params"]["duration"] = int(text) if text.isdigit() else 30
    await update.message.reply_text(
        "Введите длительность видео в секундах или оставьте пустым:"
    )
    return ASK_FPS


async def ask_fps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["video_params"]["fps"] = int(text) if text.isdigit() else 20
    await update.message.reply_text("Введите FPS видео или оставьте пустым:")
    return ASK_NO_LEGEND


async def ask_no_legend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    context.user_data["video_params"]["no_legend"] = text.startswith(
        "д"
    ) or text.startswith("y")
    await update.message.reply_text("Отключить легенду? (да/нет)")
    return ASK_CURRENCY


async def ask_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["video_params"]["currency"] = text if text else "$"
    await update.message.reply_text("Введите символ валюты или оставьте пустым:")
    return ASK_TITLE


async def ask_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["video_params"]["title"] = text
    await update.message.reply_text("Введите заголовок видео или оставьте пустым:")
    return ASK_UNDER_TITLE


async def ask_under_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["video_params"]["under_title"] = text
    await update.message.reply_text("Введите подзаголовок видео или оставьте пустым:")
    return CONFIRM_RUN


# --- Запуск пайплайна ---
async def run_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Запускаем сборку видео. Это может занять время...")
    params = context.user_data["video_params"]

    # формируем аргументы sys.argv для твоего main()
    args_list = ["script_name.py"]
    if params.get("tickers"):
        args_list += ["--tickers"] + params["tickers"]
    if params.get("start_date"):
        args_list += ["--start_date", params["start_date"]]
    if params.get("end_date"):
        args_list += ["--end_date", params["end_date"]]
    if params.get("with_investments"):
        args_list.append("--with_investments")
    if params.get("use_gradient"):
        args_list.append("--use_gradient")
    args_list += ["--initial_investment", str(params.get("initial_investment", 10000))]
    args_list += ["--monthly_investment", str(params.get("monthly_investment", 0))]
    args_list += ["--yearly_investment", str(params.get("yearly_investment", 0))]
    args_list += ["--value_col", params.get("value_col", "CAPITAL_REINVEST")]
    args_list += ["--duration", str(params.get("duration", 30))]
    args_list += ["--fps", str(params.get("fps", 20))]
    if params.get("no_legend"):
        args_list.append("--no_legend")
    args_list += ["--currency", params.get("currency", "$")]
    if params.get("title"):
        args_list += ["--title", params.get("title")]
    if params.get("under_title"):
        args_list += ["--under_title", params.get("under_title")]

    sys.argv = args_list
    await asyncio.get_event_loop().run_in_executor(None, main)

    await context.bot.send_message(
        chat_id=variables_conf.ADMIN_ID,
        text="Видео собрано! Смотрите файл: graph_with_green.mp4",
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Создание видео отменено.", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


conv_handler = ConversationHandler(
    entry_points=[CommandHandler("create_graph", create_graph_command)],
    states={
        ASK_TICKERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_tickers)],
        ASK_START_DATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_start_date)
        ],
        ASK_END_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_end_date)],
        ASK_WITH_INVESTMENTS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_with_investments)
        ],
        ASK_USE_GRADIENT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_use_gradient)
        ],
        ASK_INITIAL_INVESTMENT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_initial_investment)
        ],
        ASK_MONTHLY_INVESTMENT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_monthly_investment)
        ],
        ASK_YEARLY_INVESTMENT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_yearly_investment)
        ],
        ASK_VALUE_COL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_value_col)],
        ASK_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_duration)],
        ASK_FPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_fps)],
        ASK_NO_LEGEND: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_no_legend)],
        ASK_CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_currency)],
        ASK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_title)],
        ASK_UNDER_TITLE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_under_title)
        ],
        CONFIRM_RUN: [CommandHandler("run_video", run_video)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
