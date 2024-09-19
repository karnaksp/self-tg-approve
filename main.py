import logging
import random
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from telegram.error import TelegramError
from colorlog import ColoredFormatter

TOKEN = "7239925662:AAHqJzk9AXcIRCNMt2SKb2gzQe1rHQIM32k"
CHANNEL_ID = "-1002211156231"
ADMIN_ID = 631336613
photo_expected = False


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


async def start(update: Update, context):
    message = "Доброе утро, солнышко! Присаживайся, выбирай команду."
    await update.message.reply_text(message)
    logger.info(f"Пользователю {update.message.from_user.id} отправлено приветственное")


async def send_custom_sticker(update: Update, context):
    user_id = update.message.from_user.id
    if user_id == ADMIN_ID:
        if context.args:
            sticker_id = context.args[0]

            try:
                await context.bot.send_sticker(chat_id=CHANNEL_ID, sticker=sticker_id)
                await update.message.reply_text("Стикер успешно отправлен в канал.")
            except TelegramError as e:
                await update.message.reply_text(f"Ошибка при отправке стикера: {e}")
        else:
            await update.message.reply_text(
                "Пожалуйста, укажите ID стикера для отправки."
            )
    else:
        await update.message.reply_text(
            "У вас нет прав для отправки стикеров от имени бота."
        )


async def info(update: Update, context):
    message = (
        "Здравствуйте! ✨ Я секретутка Денис, и я помогу вам получить доступ к его личному аналу (такие шутки тут можно) — моего хозяина. "
        "Чтобы присоединиться к этому эксклюзивному сообществу, вам нужно выполнить несколько простых шагов:\n\n"
        "1️⃣ Отправьте мне самый смешной мем, который у вас есть по команде /join_request . 🎉\n"
        "2️⃣ Я передам его на рассмотрение Денису. 👨‍💼\n"
        "3️⃣ Если Денису ваш мем понравится, я с радостью предоставлю вам доступ к его каналу! 🚪\n"
        "4️⃣ Если у вас возникли какие-либо вопросы, просто используйте команду /help, потому что она не поддерживается! 💁‍♀️\n\n"
        "Удачи, и попутного ветра в сраку! 😊"
    )
    await update.message.reply_text(message)
    logger.info(
        f"Пользователю {update.message.from_user.id} отправлено сообщение с инструкцией доступа"
    )


async def get_channel_info(context):
    try:
        chat = await context.bot.get_chat(CHANNEL_ID)
        logger.info(f"Информация о канале: {chat}")
    except TelegramError as e:
        logger.error(f"Ошибка при получении информации о канале: {e}")


async def join_request(update: Update, context):
    global photo_expected
    photo_expected = True
    await get_channel_info(context)
    await update.message.reply_text(
        "Здравствуй, милый! За вход надо платить: отправь мне смешной мем, чтобы пройти."
    )
    logger.info(
        f"Пользователю {update.message.from_user.id} отправлено приветственное сообщение"
    )


async def coffee(update: Update, context):
    options = [
        "https://www.youtube.com/watch?v=7XXu_-eoxHo",
        "https://www.youtube.com/watch?v=JxhvP1Mq9Gs",
        "https://www.youtube.com/watch?v=wxtvI_1i7V0",
    ]
    selected_media = random.choice(options)
    await context.bot.send_message(update.message.chat_id, selected_media)
    logger.info(
        f"Пользователю {update.message.from_user.id} отправлена случайная YouTube ссылка"
    )


async def handle_message(update: Update, context):
    message = update.message
    user_id = message.from_user.id
    logger.info(f"Получено сообщение от пользователя {user_id}")

    if photo_expected:
        if message.photo:
            photo_id = message.photo[-1].file_id
            logger.debug(f"Фото ID: {photo_id} от пользователя {user_id}")

            keyboard = [
                [InlineKeyboardButton("Одобрить", callback_data=f"approve_{user_id}")],
                [InlineKeyboardButton("Отказать", callback_data=f"reject_{user_id}")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_photo(
                ADMIN_ID,
                photo_id,
                caption=f"Запрос от пользователя {user_id}",
                reply_markup=reply_markup,
            )
            logger.info(f"Фото от {user_id} отправлено администратору {ADMIN_ID}")
            photo_expected = False
        else:
            await message.reply_text("Это не мем!!!! (╬ಠ益ಠ)\n\nМне нужна картинка!")
            logger.warning(
                f"Пользователь {message.chat.username} отправил не фото а написал: '{message.text}'"
            )


async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()

    if "approve_" in query.data:
        user_id = query.data.split("_")[1]
        logger.info(f"Одобрение запроса пользователя {user_id}")
        try:
            invite_link = await context.bot.create_chat_invite_link(CHANNEL_ID)
            await context.bot.send_message(
                user_id,
                f"Было смешно (или возбуждающе). Проходи по ссылке!: {invite_link.invite_link}",
            )
            await query.message.reply_text(f"Пользователь {user_id} одобрен!")
            logger.info(f"Пользователь {user_id} одобрен для вступления в канал")
        except Exception as e:
            await query.message.reply_text(f"Ошибка при одобрении: {e}")
            logger.error(f"Ошибка при одобрении пользователя {user_id}: {e}")

    elif "reject_" in query.data:
        user_id = query.data.split("_")[1]
        logger.info(f"Отказ в запросе пользователя {user_id}")

        try:
            await context.bot.send_message(user_id, "Твой мем не смешной! (¬_¬ )")
            logger.info(f"Пользователю {user_id} отправлено сообщение об отказе")
            await query.message.reply_text(f"Пользователю {user_id} отказано!")
        except Exception as e:
            await query.message.reply_text(f"Ошибка при отказе: {e}")
            logger.error(f"Ошибка при отказе пользователя {user_id}: {e}")


def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("sendsticker", send_custom_sticker))
    application.add_handler(CommandHandler("join_request", join_request))
    application.add_handler(CommandHandler("coffee", coffee))
    application.add_handler(MessageHandler(filters.PHOTO, handle_message))
    application.add_handler(MessageHandler(~filters.PHOTO, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    logger.info("Бот запущен и ожидает новые сообщения")
    application.run_polling()


if __name__ == "__main__":
    main()
