from sqlalchemy.orm import Session
from config import ffmpeg_path
from rest import DOWNLOAD_DIR
from yt_dlp import YoutubeDL
from db import User

import subprocess
import asyncio
import logging
import json
import os
import re

from database import create_info

cookies_file = os.path.abspath("cookies.txt")


async def sanitize_filename(filename):
    """
        Удаляет недопустимые символы из имени файла и пути для совместимости с файловой системой.

        Args:
            filename: Имя файла в виде строки

        Returns:
            str: Отформатированную строку.
        """
    # Удаляем URL-адреса (http, https, www)
    text = re.sub(r"https?://\S+|www\.\S+|@\w+", "", filename)
    # Заменяем недопустимые символы на "_"
    sanitized = re.sub(r'[@<>:"/\\|?*]', '_', text)
    return re.sub(r"\s+", " ", sanitized).strip()


async def download_and_merge_by_format(db: Session, user_id: int, format_id: str) -> str:
    """
    Скачивает видео и аудио по выбранному формату, объединяет их и возвращает путь к итоговому файлу.

    Args:
        db (Session): Сессия SQLAlchemy для работы с базой данных.
        user_id (int): ID пользователя Telegram.
        format_id (str): ID выбранного формата.

    Returns:
        set: Путь к итоговому объединенному файлу, информация о файле.
    """

    def sync_download():
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
            'format': f"{format_id}+bestaudio/best",
            'merge_output_format': 'mp4',
            'outtmpl': os.path.join(DOWNLOAD_DIR, f"{title}-%(resolution)s{video_id}.%(ext)s"),  # Имя файлов
            'ffmpeg_location': ffmpeg_path,
            'socket_timeout': 60,
            'retries': 5,
            'nocheckcertificate': True,
            'postprocessors': [],  # Отключаем автоматическое объединение
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)\
                                                                            Chrome/120.0.0.0 Safari/537.36',
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
        # except utils.ExtractorError as e:
        #     logging.info(f'__yout.py__79__ Video format problem')
        #     return None, f'У видео проблема с форматами. Ошибка {e}'
        # except utils.DownloadError as e:
        #     logging.info(f'__yout.py__82__ Video download problem')
        #     return None, f'У видео проблема с загрузкой. Ошибка {e}'
        except Exception as e:
            logging.error(f"❌ Ошибка при скачивании видео: {e}", exc_info=True)  # <-- Выводим всю инфу об ошибке
            return None, f'Ошибка: {e}'

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
        if not file_abs or not os.path.exists(file_abs):
            raise FileNotFoundError(f"Файл {file_abs} не найден.")
        return output_file, video_info

    return await asyncio.to_thread(sync_download)


async def get_video_info(url):
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
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)\
                                                                        Chrome/120.0.0.0 Safari/537.36',
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
        channel_id = info.get("channel_id", "ID не найден")
        channel_name = info.get("channel", "Название не найдено")

        # Проверяем наличие аудиоформатов
        formats = info.get('formats', [])
        audio_formats = [
            f for f in formats
            if f.get("acodec") != "none" and f.get("vcodec") == "none" and f.get("filesize")
        ]

        # Ищем аудиоформат с максимальным размером файла
        if audio_formats:
            best_audio = max(audio_formats, key=lambda f: f['filesize'])

        # with open("video_info.json", "w", encoding="utf-8") as f:
        #     json.dump(info, f, indent=4, ensure_ascii=False)

        return best_audio['format_id'], best_audio['filesize'], title, thumbnail, info, video_id, channel_id, channel_name


async def filter_best_formats(formats, video_id):
    """
    Фильтрует список форматов, оставляя только один лучший формат на каждое разрешение.
    Убирает форматы без размера файла и без видеокодека.
    """
    best_formats = {}

    for f in formats:
        resolution = f"{f.get('width', 'N/A')}x{f.get('height', 'N/A')}"
        vcodec = f.get("vcodec", "unknown")
        filesize = f.get("filesize", 0)  # Размер в байтах
        bitrate = f.get("tbr", 0)  # Битрейт в kbps

        # Пропускаем форматы без размера файла или без видеокодека
        if not filesize or vcodec == "none":
            continue

        # Если такого разрешения еще нет в словаре — добавляем
        if resolution not in best_formats or bitrate > best_formats[resolution]["tbr"]:
            best_formats[resolution] = {
                "format_id": f.get("format_id", "N/A"),
                "extension": f.get("ext", "N/A"),
                "resolution": resolution,
                "vcodec": vcodec,
                "filesize": f"{round(filesize / (1024 ** 2), 2)} MB",
                "tbr": bitrate
            }
    return list(best_formats.values())


async def convert_webm_to_m4a(input_file: str) -> str:
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


async def filter_unique_formats(formats):
    """
    Убирает дубликаты форматов с одинаковыми разрешением и кодеком, оставляя наибольший размер.
    """
    unique_formats = {}

    for f in formats:
        resolution = f.get("resolution", f"{f.get('width', 'N/A')}x{f.get('height', 'N/A')}")
        vcodec = f.get("vcodec", "none")
        key = (resolution, vcodec)  # Используем разрешение и кодек как ключ

        if key not in unique_formats or f.get("filesize", 0) > unique_formats[key].get("filesize", 0):
            unique_formats[key] = f

    return list(unique_formats.values())  # Возвращаем список без дубликатов