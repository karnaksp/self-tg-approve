import logging
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
import os
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "7239925662:AAHqJzk9AXcIRCNMt2SKb2gzQe1rHQIM32k"
CHANNEL_ID = "@-1002211156231"
ADMIN_ID = "631336613"

# Подключение к MongoDB Atlas
MONGO_URI = "mongodb+srv://faucdenis:Jw6wRr8dbpcIoVBx@cluster0.98uhk.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["telegram_bot_db"]
requests_collection = db["requests"]


# Функция для отправки заявки администратору
async def handle_message(update: Update, context: CallbackContext):
    message = update.message
    if message.photo:
        user_id = message.from_user.id
        photo_id = message.photo[-1].file_id

        # Сохранение заявки в MongoDB
        request_data = {"user_id": user_id, "photo_id": photo_id, "status": "pending"}
        requests_collection.insert_one(request_data)

        # Отправляем изображение администратору с кнопкой одобрения
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
    else:
        await message.reply_text("Это не мем!!!! (╬ಠ益ಠ)")


# Обработчик нажатия кнопки
async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    # Обрабатываем нажатие кнопки "Одобрить"
    if "approve_" in query.data:
        user_id = query.data.split("_")[1]

        # Проверяем наличие заявки в MongoDB
        request = requests_collection.find_one(
            {"user_id": int(user_id), "status": "pending"}
        )

        if request:
            # Одобряем заявку на вступление
            try:
                await context.bot.approve_chat_join_request(CHANNEL_ID, user_id)
                await query.message.reply_text(f"Пользователь {user_id} одобрен!")
                requests_collection.update_one(
                    {"user_id": int(user_id)}, {"$set": {"status": "approved"}}
                )
            except TelegramError as e:
                await query.message.reply_text(f"Ошибка при одобрении: {e}")
        else:
            await query.message.reply_text(
                f"Заявка от пользователя {user_id} уже обработана или не найдена."
            )


# Обработчик команды start
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Привет! Отправь мне мем, чтобы я мог одобрить твою заявку на вступление в канал."
    )


# Функция обработки оставшихся заявок после перезапуска бота
async def process_pending_requests(context: CallbackContext):
    pending_requests = requests_collection.find({"status": "pending"})

    for request in pending_requests:
        user_id = request["user_id"]
        photo_id = request["photo_id"]

        # Отправляем администратору для обработки
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


# Главная функция
async def main():
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Обрабатываем зависшие заявки после перезапуска
    application.job_queue.run_once(process_pending_requests, 1)

    # Запуск бота через run_polling
    await application.initialize()
    await application.start()
    await application.process_updates()
    await application.stop()


# Запуск в существующем event loop
if __name__ == "__main__":
    try:
        asyncio.get_running_loop()
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(main())
