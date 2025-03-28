from aiogram.client.telegram import TelegramAPIServer
from aiogram.client.session.aiohttp import AiohttpSession
import logging
import os

#Local
#session = AiohttpSession()

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

