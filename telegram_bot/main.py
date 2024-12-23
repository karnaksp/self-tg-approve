"""
Сборка бота
"""

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

import variables_conf
from commands import (
    coffee,
    info,
    join_request,
    send_sticker_request,
    start,
    start_talk,
    stop_talk,
)
from handlers import button_handler, handle_message, handle_sticker, handle_talk


def main():
    application = Application.builder().token(variables_conf.TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("sendsticker", send_sticker_request))
    application.add_handler(CommandHandler("join_request", join_request))
    application.add_handler(CommandHandler("coffee", coffee))
    application.add_handler(CommandHandler("talk", start_talk))
    application.add_handler(CommandHandler("talk_rag", start_talk))
    application.add_handler(CommandHandler("stop_talk", stop_talk))
    # application.add_handler(CommandHandler("upload_pdf", upload_pdf))
    application.add_handler(MessageHandler(filters.TEXT, handle_talk))
    application.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    application.add_handler(MessageHandler(None, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))

    # job_queue = application.job_queue
    # job_queue.run_repeating(check_inactive_sessions, interval=100)

    application.run_polling()


if __name__ == "__main__":
    main()
