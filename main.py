import logging
from logging import StreamHandler
from colorlog import ColoredFormatter
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    CallbackContext,
)
from telegram.error import TelegramError
import asyncio


def setup_logger():
    handler = StreamHandler()
    formatter = ColoredFormatter(
        "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    )
    handler.setFormatter(formatter)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    return logger


logger = setup_logger()

TOKEN = "7239925662:AAHqJzk9AXcIRCNMt2SKb2gzQe1rHQIM32k"
CHANNEL_ID = "@-1002211156231"
ADMIN_ID = "631336613"
MONGO_URI = "mongodb+srv://faucdenis:Jw6wRr8dbpcIoVBx@cluster0.98uhk.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client["telegram_bot_db"]
requests_collection = db["requests"]


# Функция для отправки заявки администратору
async def handle_message(update: Update, context: CallbackContext):
    message = update.message
    user_id = message.from_user.id
    logger.info(f"Получено сообщение от пользователя {user_id}")

    if message.photo:
        photo_id = message.photo[-1].file_id
        logger.debug(f"Фото ID: {photo_id} от пользователя {user_id}")
        request_data = {"user_id": user_id, "photo_id": photo_id, "status": "pending"}
        requests_collection.insert_one(request_data)
        logger.info(f"Заявка от пользователя {user_id} сохранена в базу данных")
        keyboard = [
            [InlineKeyboardButton("Одобрить", callback_data=f"approve_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_photo(
            ADMIN_ID,
            photo_id,
            caption=f"Запрос от пользователя {user_id}",
            reply_markup=reply_markup,
        )
        logger.info(f"Фото от {user_id} отправлено администратору {ADMIN_ID}")
    else:
        await message.reply_text("Это не мем!!!! (╬ಠ益ಠ)")
        logger.warning(f"Пользователь {user_id} отправил не фото")


async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if "approve_" in query.data:
        user_id = query.data.split("_")[1]
        logger.info(f"Одобрение запроса пользователя {user_id}")
        request = requests_collection.find_one(
            {"user_id": int(user_id), "status": "pending"}
        )

        if request:
            try:
                await context.bot.approve_chat_join_request(CHANNEL_ID, user_id)
                await query.message.reply_text(f"Пользователь {user_id} одобрен!")
                logger.info(f"Пользователь {user_id} одобрен для вступления в канал")
                requests_collection.update_one(
                    {"user_id": int(user_id)}, {"$set": {"status": "approved"}}
                )
                logger.debug(
                    f"Статус заявки пользователя {user_id} обновлён на 'approved'"
                )
            except TelegramError as e:
                await query.message.reply_text(f"Ошибка при одобрении: {e}")
                logger.error(f"Ошибка при одобрении пользователя {user_id}: {e}")
        else:
            await query.message.reply_text(
                f"Заявка от пользователя {user_id} уже обработана или не найдена."
            )
            logger.warning(
                f"Заявка от пользователя {user_id} уже обработана или не найдена"
            )


async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Привет! Отправь мне мем, чтобы я мог одобрить твою заявку на вступление в канал."
    )
    logger.info(
        f"Пользователю {update.message.from_user.id} отправлено приветственное сообщение"
    )


async def process_pending_requests(context: CallbackContext):
    logger.info("Обработка зависших заявок начата")
    pending_requests = requests_collection.find({"status": "pending"})

    for request in pending_requests:
        user_id = request["user_id"]
        photo_id = request["photo_id"]
        logger.debug(
            f"Заявка от пользователя {user_id} с фото {photo_id} ожидает обработки"
        )

        keyboard = [
            [InlineKeyboardButton("Одобрить", callback_data=f"approve_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_photo(
            ADMIN_ID,
            photo_id,
            caption=f"Запрос от пользователя {user_id}",
            reply_markup=reply_markup,
        )
        logger.info(
            f"Заявка от пользователя {user_id} повторно отправлена администратору"
        )


async def main():
    try:
        application = Application.builder().token(TOKEN).build()

        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.PHOTO, handle_message))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.job_queue.run_once(process_pending_requests, 1)
        logger.info("Запланирована обработка зависших заявок через 1 секунду")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        logger.info("Бот запущен и ожидает новые сообщения")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logger.info("Завершение работы секретутки")
    except Exception as e:
        logger.error(f"Ошибка в основной функции: {e}")


if __name__ == "__main__":
    try:
        asyncio.get_running_loop()
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(main())
