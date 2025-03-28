import os
import re
import surrogates
from aiogram.types import FSInputFile

import logging


def make_a_folders():
    DOWNLOAD_DIR = "videos"
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    return DOWNLOAD_DIR

def is_under_2gb(size_str):
    match = re.search(r"([\d.]+)\s*(MB|GB)", size_str, re.IGNORECASE)  # Извлекаем число и единицу измерения
    if not match:
        logging.debug(f'Не удалось проверить размер запрашиваемого файла')
        return False  # Если формат неправильный, возвращаем False

    size, unit = float(match.group(1)), match.group(2).upper()

    if unit == "GB":
        size *= 1024  # Переводим гигабайты в мегабайты

    return size >= 2048  # Проверяем, не больше ли 2 ГБ

def delete_keyboard_message(user_id: int):
    if user_id in user_messages:
        try:
            logging.info(f"Сообщение с клавиатурой у {user_id} пользователя удалено")
            return True
        except Exception as e:
            logging.warning(f"Ошибка удаления сообщения с клавиатурой {user_id}: {e}")
            return False

# Список эмодзи для отображения информации
EMOJIS = {
    'title': surrogates.decode('\U0001F3AD'),
    'autor': surrogates.decode('\U0001F464'),
    'view': surrogates.decode('\U0001F453'),
    'durations': surrogates.decode('\U0001F566"'),
    'date': surrogates.decode('\U0001F3AC'),
    'resolutions': surrogates.decode('\U0001F3A5'),
    'size': surrogates.decode('\U0001F4BE'),
    'download': surrogates.decode('\U0001F4E5'),
    'wait': surrogates.decode('\u231B'),
    'tv': surrogates.decode('\U0001F4FA'),
    'warning': surrogates.decode('\u26A0'),
    'start': surrogates.decode('\U0001F4E5'),
    'sound': surrogates.decode('\U0001f3b6')
}

# Переменные для сообщений об ошибке
ERROR_IMAGE = FSInputFile(os.path.abspath("images/error.webp"))
FAILS_IMAGE = FSInputFile(os.path.abspath("images/invalid_input.webp"))
LOAD_IMAGE = FSInputFile(os.path.abspath("images/loading.webp"))
START_IMAGE = FSInputFile(os.path.abspath("images/start_hello.webp"))
ERROR_TEXT = f"Что-то пошло не так, попробуйте позже..."

# Регулярные выражения для поиска ссылок
YOUTUBE_REGEX = r"(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/\S+"
TIKTOK_REGEX = r"(https?:\/\/)?(www\.)?(tiktok\.com)\/\S+"
VK_VIDEO_REGEX = r"(https?://)?(www\.)?(vk\.com|vkvideo\.ru)/video[-\d]+_\d+"

INFO_MESSAGE = " Получаю информацию о видео..."
DOWNLOAD_DIR = make_a_folders()

# Хранение идентификаторов сообщений с клавиатурой для каждого пользователя
user_messages = {}