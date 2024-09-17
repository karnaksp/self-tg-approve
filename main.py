from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from telegram.error import TelegramError
import logging
from colorlog import ColoredFormatter


def setup_logger():
    handler = logging.StreamHandler()
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
CHANNEL_ID = "@-2211156231"
ADMIN_ID = "631336613"


async def handle_message(update, context):
    message = update.message
    user_id = message.from_user.id
    logger.info(f"Получено сообщение от пользователя {user_id}")

    if message.photo:
        photo_id = message.photo[-1].file_id
        logger.debug(f"Фото ID: {photo_id} от пользователя {user_id}")

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


async def button_handler(update, context):
    query = update.callback_query
    await query.answer()

    if "approve_" in query.data:
        user_id = query.data.split("_")[1]
        logger.info(f"Одобрение запроса пользователя {user_id}")
        try:
            await context.bot.approve_chat_join_request(CHANNEL_ID, user_id)
            await query.message.reply_text(f"Пользователь {user_id} одобрен!")
            logger.info(f"Пользователь {user_id} одобрен для вступления в канал")
        except TelegramError as e:
            await query.message.reply_text(f"Ошибка при одобрении: {e}")
            logger.error(f"Ошибка при одобрении пользователя {user_id}: {e}")


async def start(update, context):
    await update.message.reply_text(
        "Привет! Отправь мне мем, чтобы я мог одобрить твою заявку на вступление в канал."
    )
    logger.info(
        f"Пользователю {update.message.from_user.id} отправлено приветственное сообщение"
    )


def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Бот запущен и ожидает новые сообщения")

    application.run_polling()


if __name__ == "__main__":
    main()
