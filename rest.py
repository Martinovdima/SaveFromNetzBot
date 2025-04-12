import os
import re
import surrogates
from aiogram.types import FSInputFile
from urllib.parse import urlparse, parse_qs

import logging

async def convert_size_to_bytes(size_str: str) -> int:
    if not size_str.endswith(" MB"):
        raise ValueError("Неверный формат строки размера. Ожидался формат 'X.XX MB'.")

    size_in_mb = float(size_str.replace(" MB", "").strip())  # Убираем "MB" и конвертируем в float
    size_in_bytes = int(size_in_mb * (1024 ** 2))  # Переводим в байты
    return size_in_bytes

def is_playlist_url(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    return 'list' in query_params  # Если есть параметр 'list', это плейлист

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
    'sound': surrogates.decode('\U0001f3b6'),
    'fire': f'{surrogates.decode('\u26A1')} fast'
}

# Переменные для сообщений об ошибке
ERROR_IMAGE = FSInputFile(os.path.abspath("images/error.webp"))
FAILS_IMAGE = FSInputFile(os.path.abspath("images/invalid_input.webp"))
LOAD_IMAGE = FSInputFile(os.path.abspath("images/loading.webp"))
START_IMAGE = FSInputFile(os.path.abspath("images/start_hello.webp"))
ERROR_TEXT = f"Что-то пошло не так, попробуйте позже..."

# Регулярные выражения для поиска ссылок
YOUTUBE_REGEX = r"(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?v=|shorts\/)|youtu\.be\/)[\w\-]+"
YOUTUBE_CHANNEL_REGEX = r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/(channel|c|user)\/[a-zA-Z0-9_-]+"
TIKTOK_REGEX = r"(https?:\/\/)?(www\.)?(tiktok\.com)\/\S+"
VK_VIDEO_REGEX = r"(https?://)?(www\.)?(vk\.com|vkvideo\.ru)/(video[-\d_]+|playlist/[-\d_]+/video[-\d_]+)"

INFO_MESSAGE = " Получаю информацию о видео..."
DOWNLOAD_DIR = make_a_folders()

# Хранение идентификаторов сообщений с клавиатурой для каждого пользователя
user_messages = {}