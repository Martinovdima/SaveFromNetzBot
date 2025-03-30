from aiogram.client.telegram import TelegramAPIServer
from aiogram.client.session.aiohttp import AiohttpSession
import logging
import os
from dotenv import load_dotenv

#Local
#session = AiohttpSession()
load_dotenv()  # Загружаем переменные из .env

#Server
session = AiohttpSession(api=TelegramAPIServer.from_base('http://localhost:8081'))

# Настройка логирования в файл
logging.basicConfig(
                level=logging.DEBUG,
                filename="py_log.log",
                filemode="a",  # "a" - добавлять в файл, "w" - перезаписывать
                format="%(asctime)s - %(levelname)s - %(message)s"
            )

ffmpeg_path = os.path.abspath("ffmpeg/bin/ffmpeg.exe")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

