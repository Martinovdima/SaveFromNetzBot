import os
import re

import emoji
import subprocess

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from yt_dlp import YoutubeDL
from db import User
from sqlalchemy.orm import Session

from rest import EMOJIS, DOWNLOAD_DIR

def sanitize_filename(filename):
    """
        Удаляет недопустимые символы из имени файла и пути для совместимости с файловой системой.

        Args:
            filename (str): Имя файла в виде строки

        Returns:
            str: Отформатированную строку.
        """
    # Удаляем URL-адреса (http, https, www)
    text = re.sub(r"https?://\S+|www\.\S+|@\w+", "", filename)
    # Заменяем недопустимые символы на "_"
    sanitized = re.sub(r'[@<>:"/\\|?*]', '_', text)
    return re.sub(r"\s+", " ", sanitized).strip()

def download_and_merge_by_format(db: Session, user_id: int, format_id: str) -> str:
    """
    Скачивает видео и аудио по выбранному формату, объединяет их и возвращает путь к итоговому файлу.

    Args:
        db (Session): Сессия SQLAlchemy для работы с базой данных.
        user_id (int): ID пользователя Telegram.
        format_id (str): ID выбранного формата.

    Returns:
        str: Путь к итоговому объединенному файлу.
    """
    ffmpeg_path = os.path.abspath("ffmpeg/bin/ffmpeg.exe")
    os.environ["PATH"] += os.pathsep + os.path.dirname(ffmpeg_path)
    # Получаем URL пользователя из базы данных
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user or not user.url:
        raise ValueError("Ссылка не найдена в базе данных. Отправьте её ещё раз.")

    url = user.url
    title = user.title
    video_id = user.video_id
    # Настройки для скачивания видео и аудио
    ydl_opts = {
        'cookiefile': "cookies.txt",
        'verbose': True,
        'format': f"{format_id}+bestaudio/best",  # Скачивание видео и аудио
        'outtmpl': os.path.join(DOWNLOAD_DIR, f"{title}-%(resolution)s{video_id}.%(ext)s"),  # Имя файлов
        'ffmpeg_location': ffmpeg_path,
        'socket_timeout': 60,
        'retries': 5,
        'nocheckcertificate': True,
        'postprocessors': [],  # Отключаем автоматическое объединение
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'extractor_args': {
            'youtube': {
                'formats': 'missing_pot'
            }
        }
    }

    # Скачивание видео и аудио
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            resolution = info.get('resolution', 'unknown')
            ext = info.get('ext', 'mkv')  # Если не найдено расширение, по умолчанию 'mkv'
    except Exception as e:
        raise RuntimeError(f"Ошибка при скачивании: {e}")

    # Проверяем, что формат существует
    formats = info.get("formats", [])
    format_info = next((f for f in formats if f["format_id"] == format_id), None)
    if not format_info:
        raise ValueError(f"Формат с ID {format_id} не найден.")

    # Формируем результат
    video_info = {
        "title": info.get("title", "Без названия"),
        "uploader": info.get("uploader", "Неизвестен"),
        "view_count": info.get("view_count", "Нет данных"),
        "duration": info.get("duration", 0),
        "upload_date": info.get("upload_date", "Нет данных"),
        "thumbnail": info.get("thumbnail", ""),
        "format_id": format_info.get("format_id"),
        "extension": format_info.get("ext"),
        "resolution": format_info.get("resolution", "Нет данных"),
        "vcodec": format_info.get("vcodec", "Нет данных"),
        "acodec": format_info.get("acodec", "Нет данных"),
        "filesize": format_info.get("filesize", "Нет данных"),
    }

    output_file = os.path.join(DOWNLOAD_DIR, f"{title}-{resolution}{video_id}.{ext}")
    # Проверяем, что файл существует
    file_abs = os.path.abspath(output_file)
    #
    if not file_abs or not os.path.exists(file_abs):
        raise FileNotFoundError(f"Файл {file_abs} не найден.")
    return output_file, video_info

def get_video_info(url):
    """
    Получает информацию о видео из YouTube с помощью yt-dlp.

    Args:
        url (str): Ссылка на видео.

    Returns:
        tuple: Кортеж из:
            - str: Лучший формат аудио.
            - int: Размер аудиофайла (в байтах).
            - str: Название видео.
            - str: Ссылка на миниатюру (обложку).
            - dict: Полная информация о видео.
            - str: ID видео.

    """
    ydl_opts = {
        'cookiefile': "cookies.txt",
        'verbose': True,
        'noplaylist': True,  # Только одно видео
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'extractor_args': {
            'youtube': {
                'formats': 'missing_pot'
            }
        }
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        # id видео
        video_id = info.get("id", "Неизвестно")

        # Название видео
        title = info.get('title', 'Без названия')

        # Миниатюра
        thumbnail = info.get('thumbnail', '')

        # Проверяем наличие аудиоформатов
        formats = info.get('formats', [])
        audio_formats = [
            f for f in formats
            if f.get("acodec") != "none" and f.get("vcodec") == "none" and f.get("filesize")
        ]

        # Ищем аудиоформат с максимальным размером файла
        if audio_formats:
            best_audio = max(audio_formats, key=lambda f: f['filesize'])

        return best_audio['format_id'], best_audio['filesize'], title, thumbnail, info, video_id

def filter_formats_by_vcodec_and_size(audio, formats, vcodec_prefix="avc1"):
    """
    Фильтрует список видеоформатов по префиксу видеокодека и наличию размера файла.

    Args:
        audio (int | float | None): Размер аудиофайла в байтах или None, если неизвестен.
        formats (list[dict]): Список форматов, полученный из yt-dlp.
        vcodec_prefix (str, optional): Префикс видеокодека для фильтрации (по умолчанию "avc1").

    Returns:
        list[dict]: Отфильтрованный список форматов с полями:
            - format_id (str): ID формата.
            - extension (str): Расширение файла (например, "mp4").
            - resolution (str): Разрешение (например, "1920x1080").
            - vcodec (str): Видеокодек.
            - filesize (str): Общий размер (включая аудио) в мегабайтах (например, "12.5 MB").

    """
    filtered_formats = []
    if isinstance(audio, (int, float)):
        audio_size = audio
    else:
        audio_size = 0

    for f in formats:
        vcodec = f.get("vcodec", "")
        filesize = f.get("filesize", None)
        if vcodec.startswith(vcodec_prefix) and filesize:  # Проверяем, начинается ли vcodec с "avc1" и есть ли размер
            format_id = f.get("format_id", "N/A")
            ext = f.get("ext", "N/A")
            resolution = f.get("resolution", f"{f.get('width', 'N/A')}x{f.get('height', 'N/A')}")
            total_size = filesize + audio_size
            filesize_str = f"{round(total_size / (1024 ** 2), 2)} MB"  # Преобразуем размер в MB

            # Сохраняем формат с подробной информацией
            filtered_formats.append({
                "format_id": format_id,
                "extension": ext,
                "resolution": resolution,
                "vcodec": vcodec,
                "filesize": filesize_str,
            })

    return filtered_formats

def main_kb(filtered_formats, audio_id, audio_size):
    """
    Формирует клавиатуру с кнопками для скачивания аудио и видео.

    Args:
        filtered_formats (list[dict]): Список словарей с форматами видео.
        audio_id (str): ID аудиофайла.
        audio_size (int): Размер аудиофайла в байтах.

    Returns:
        InlineKeyboardMarkup: Объект клавиатуры с кнопками загрузки.
    """
    button_list = []
    button_list.append([InlineKeyboardButton(
        text=f" Cкачать {emoji.emojize(EMOJIS['sound'])} аудио {emoji.emojize(EMOJIS['size'])} {round(audio_size / (1024 ** 2), 2)} MB",
        callback_data=f"download_audio:{audio_id}")])
    for f in filtered_formats:
        format_id = ['format_id']
        if format_id:
            callback_data = f"download:{f['format_id']}"
            button_list.append([InlineKeyboardButton(
                text=f" Cкачать {emoji.emojize(EMOJIS['resolutions'])} {f['resolution']:<10} {emoji.emojize(EMOJIS['size'])}  {f['filesize']:<10}",
                callback_data=callback_data)])
    # Создаем клавиатуру с кнопками
    keyboard = InlineKeyboardMarkup(inline_keyboard=button_list)
    return keyboard

def convert_webm_to_m4a(input_file: str) -> str:
    """
    Конвертирует webm в m4a, удаляет исходный файл и возвращает путь к новому файлу.

    Args:
        input_file (str): Путь к входному .webm файлу.

    Returns:
        str: Путь к сконвертированному .m4a файлу.
    """
    if not input_file.lower().endswith(".webm"):
        raise ValueError("Файл должен быть в формате .webm")
        return

    # Формируем путь к выходному файлу
    output_file = input_file.rsplit(".", 1)[0] + ".m4a"

    # Формируем команду ffmpeg
    command = ["ffmpeg", "-i", input_file, "-vn", "-y", output_file]

    try:
        # Запускаем процесс конвертации
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Удаляем исходный файл .webm
        os.remove(input_file)

        return output_file
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при конвертации: {e}")
        return ""