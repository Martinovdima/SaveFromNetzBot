import os
import surrogates
from aiogram.types import FSInputFile


def make_a_folders():
    DOWNLOAD_DIR = "videos"
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    return DOWNLOAD_DIR


# Список эмодзи для  отображения информации
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
INSTAGRAM_REGEX = r"(https?:\/\/)?(www\.)?(instagram\.com|instagr\.am)\/\S+"

INFO_MESSAGE = " Получаю информацию о видео..."
DOWNLOAD_DIR = make_a_folders()
