"""
Настройки глобальных переменных
"""

import os

from dotenv import load_dotenv

load_dotenv()
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_ID = os.getenv("ADMIN_ID")
TOKEN = os.getenv("TOKEN")
PHOTO_EXPECTED_FLG = False
STIKCER_EXPECTED_FLG = False
