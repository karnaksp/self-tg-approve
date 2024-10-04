'''
Хотелось бы добавить еще фуекционал - переход на страницу, парсинг, передача в промпт в качестве источника
Пока что
Пока развернуть раг негде :)
'''

import logging
import random
import asyncio
import re
import os
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
    CallbackContext,
    filters,
    ContextTypes,
)
from telegram.error import TelegramError
from colorlog import ColoredFormatter
from ollama import AsyncClient
from datetime import datetime, timedelta

TOKEN = "7239925662:AAHqJzk9AXcIRCNMt2SKb2gzQe1rHQIM32k"
CHANNEL_ID = "-1002211156231"
ADMIN_ID = 631336613
global photo_expected, sticker_expected
photo_expected = False
sticker_expected = False
ollama_base_url = os.getenv("OLLAMA_BASE_URL")
LLM_NAME = os.getenv("LLM")
client = AsyncClient(host=ollama_base_url)

waiting_phrases = [
    "Подожди немножечко, я подумаю... 🌸",
    "Чуточку терпения, мой дорогой! 💖",
    "Маленькая пауза, скоро все будет готово! 😊",
    "Дай мне минутку, я подготавливаю ответ для тебя! ✨",
    "Ожидай, скоро я тебя удивлю! 🌟",
    "Чудеса требуют времени, не скучай! 🐰",
    "Пока ты ждешь, представь, как я улыбаюсь! 😄"
]

SYSTEM_PROMPT = "Here you play the role of a cute secretary anime-girl. \
    Only if someone ASKS how get into channel (self life-channel of Denis), \
        say that you need to click on the /join_request command or /info for instruction. \
            Otherwise you can use cute smileys in your answer, joke and tell other stories. Answer only in Russian!"


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


async def send_sticker_request(update: Update, context):
    global sticker_expected
    sticker_expected = True
    await update.message.reply_text("Пожалуйста, отправьте стикер.")
    logger.info(f"Запрос на стикер от пользователя {update.message.from_user.id}")


async def handle_sticker(update: Update, context):
    global sticker_expected
    message = update.message
    user_id = message.from_user.id
    if user_id == ADMIN_ID:
        if sticker_expected:
            if message.sticker:
                sticker_id = message.sticker.file_id
                logger.info(
                    f"Получен стикер ID: {sticker_id} от пользователя {message.chat.username}"
                )
                await context.bot.send_sticker(CHANNEL_ID, sticker_id)
                logger.info(
                    f"Стикер от {message.chat.username} отправлен в канал {CHANNEL_ID}"
                )
                sticker_expected = False
            else:
                await message.reply_text(
                    "Это не стикер! Пожалуйста, отправьте именно стикер."
                )
                logger.warning(
                    f"Пользователь {message.chat.username} отправил не стикер."
                )
        else:
            await message.reply_text(
                "Пожалуйста, сначала отправьте команду /sendsticker."
            )
            logger.warning(
                f"Пользователь {message.chat.username} попытался отправить стикер без запроса."
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
        "https://www.youtube.com/watch?v=WB_eq5uS0A0&ab_channel=SamuraiGirlD%27n%27B",
        "https://www.youtube.com/watch?v=8hx4qiOGgDE&ab_channel=PhonkDemon",
        "https://www.youtube.com/watch?v=A7WZhoGRjMI&ab_channel=Mr_MoMoMusic",
        "https://www.youtube.com/watch?v=EtD7_8kCMHA&ab_channel=Deebu",
        "https://www.youtube.com/watch?v=qvZsPYOrmh0&t=1s&ab_channel=HiddenbyLeaves",
    ]
    selected_media = random.choice(options)
    await context.bot.send_message(update.message.chat_id, selected_media)
    logger.info(
        f"Пользователю {update.message.from_user.id} отправлена случайная YouTube ссылка"
    )


async def handle_message(update: Update, context):
    global photo_expected
    message = update.message
    user_id = message.from_user.id
    logger.info(f"Получено сообщение от пользователя {message.chat.username}")

    if photo_expected:
        if message.photo:
            photo_id = message.photo[-1].file_id
            logger.debug(f"Фото ID: {photo_id} от пользователя {message.chat.username}")

            keyboard = [
                [InlineKeyboardButton("Одобрить", callback_data=f"approve_{user_id}")],
                [InlineKeyboardButton("Отказать", callback_data=f"reject_{user_id}")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_photo(
                ADMIN_ID,
                photo_id,
                caption=f"Запрос от пользователя {message.chat.username}",
                reply_markup=reply_markup,
            )
            logger.info(
                f"Фото от {message.chat.username} отправлено администратору {ADMIN_ID}"
            )
            photo_expected = False
        else:
            await message.reply_text("Это не мем!!!! (╬ಠ益ಠ)\n\nМне нужна картинка!")
            logger.warning(
                f"Пользователь {message.chat.username} отправил не фото а написал: '{message.text}'"
            )
    else:
        await message.reply_text("Не пойму, шо ты хочешь, дорогой! Выбери команду...")


async def button_handler(update: Update, context):
    query = update.callback_query
    user_name = update.message.chat.username
    await query.answer()

    if "approve_" in query.data:
        user_id = query.data.split("_")[1]
        logger.info(f"Одобрение запроса пользователя")
        try:
            invite_link = await context.bot.create_chat_invite_link(CHANNEL_ID)
            await context.bot.send_message(
                user_id,
                f"Было смешно (или возбуждающе). Проходи по ссылке!: {invite_link.invite_link}",
            )
            await query.message.reply_text(f"Пользователь {user_name} одобрен!")
            logger.info(f"Пользователь {user_name} одобрен для вступления в канал")
        except Exception as e:
            await query.message.reply_text(f"Ошибка при одобрении: {e}")
            logger.error(f"Ошибка при одобрении пользователя {user_name}: {e}")

    elif "reject_" in query.data:
        user_id = query.data.split("_")[1]
        logger.info(f"Отказ в запросе пользователя {user_name}")

        try:
            await context.bot.send_message(user_id, "Твой мем не смешной! (¬_¬ )")
            logger.info(f"Пользователю {user_name} отправлено сообщение об отказе")
            await query.message.reply_text(f"Пользователю {user_name} отказано!")
        except Exception as e:
            await query.message.reply_text(f"Ошибка при отказе: {e}")
            logger.error(f"Ошибка при отказе пользователя {user_name}: {e}")


async def llama_chat(user_message):
    response = await client.chat(
        model=LLM_NAME,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {"role": "user", "content": user_message},
        ],
        stream=False,
    )

    return response['message']['content']

async def start_talk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.chat.username
    logger.info(f"Пользователь {user_name} начал диалог через /talk")
    await update.message.reply_text("Приветики! Внимательно слушаю тебя, ебало ослиное.")
    context.user_data['in_talk'] = True
    context.user_data['last_message_time'] = datetime.now()
    context.user_data['message_history'] = []
    
async def stop_talk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.chat.username
    logger.info(f"Пользователь {user_name} завершил диалог через /stop_talk")
    await update.message.reply_text("Пока-пока ^-^.")
    context.user_data['in_talk'] = False
    context.user_data['last_message_time'] = datetime.now()
    context.user_data['message_history'] = []

async def handle_talk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('in_talk'):
        user_name = update.message.chat.username
        text = update.message.text
        context.user_data['last_message_time'] = datetime.now()
        logger.info(f"Пользователь {user_name} прислал сообщение для разговора: {text}")
        waiting_message = random.choice(waiting_phrases)
        await update.message.reply_text(waiting_message)
        
        message_history = context.user_data.get('message_history', [])
        context.user_data['message_history'] = message_history
        formatted_history = "\n".join(message_history)
        full_response = await llama_chat(f"История последних сообщений:\n{formatted_history}\n\nНовое сообщение:\n{text}")
        
        message_history.append(text)
        if len(message_history) > 5:
            message_history.pop(0)

        words = full_response.split()
        message_parts = []
        chunk = []
        total_words = 0

        for word in words:
            chunk.append(word)
            total_words += 1
            if total_words >= 50 and re.search(r'[.!?]', word):
                message_parts.append(' '.join(chunk))
                chunk = []
                total_words = 0
        if chunk:
            message_parts.append(' '.join(chunk))
        for part in message_parts:
            await update.message.reply_text(part)
            await asyncio.sleep(1)
    else:
        # Если пользователь не в режиме разговора, игнорируем или обрабатываем другое сообщение
        pass

async def check_inactive_sessions(context: CallbackContext):
    now = datetime.now()
    for user_id, user_data in context.application.user_data.items():
        if user_data.get('in_talk') and user_data.get('last_message_time'):
            last_message_time = user_data['last_message_time']
            if (now - last_message_time).total_seconds() > 300:
                user_data['in_talk'] = False
                await context.bot.send_message(
                    user_id, "Ты слишком долго молчал... пока-пока (；ω；)"
                )
                logger.info(f"Сессия разговора завершена из-за неактивности для пользователя {user_id}")


def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("sendsticker", send_sticker_request))
    application.add_handler(CommandHandler("join_request", join_request))
    application.add_handler(CommandHandler("coffee", coffee))
    application.add_handler(CommandHandler("talk", start_talk))
    application.add_handler(CommandHandler("stop_talk", stop_talk))
    
    application.add_handler(MessageHandler(filters.TEXT, handle_talk))
    application.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    application.add_handler(MessageHandler(filters.PHOTO, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))  
    
    job_queue = application.job_queue
    job_queue.run_repeating(check_inactive_sessions, interval=100)
    logger.info("Бот запущен и ожидает новые сообщения")

    application.run_polling()


if __name__ == "__main__":
    main()
