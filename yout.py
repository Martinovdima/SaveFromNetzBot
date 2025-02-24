import logging
import os
import re

import emoji
import subprocess

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from yt_dlp import YoutubeDL, utils
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
        set: Путь к итоговому объединенному файлу, информация о файле.
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
    except utils.ExtractorError as e:
        logging.info(f'__yout.py__79__ Video format problem')
        return None, f'У видео проблема с форматами. Ошибка {e}'
    except utils.DownloadError as e:
        logging.info(f'__yout.py__82__ Video download problem')
        return None, f'У видео проблема с загрузкой. Ошибка {e}'
    except Exception as e:
        logging.info(f'__yout.py__85__ Video is not availibale in country')
        return None, f'Данное видео заблокированно в регионе. Ошибка {e}'

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
    print(output_file)
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
    Также добавляет лучший аудиоформат в начало списка.

    Args:
        audio (int | float | None): Размер аудиофайла в байтах или None, если неизвестен.
        formats (list[dict]): Список форматов, полученный из yt-dlp.
        vcodec_prefix (str, optional): Префикс видеокодека для фильтрации (по умолчанию "avc1").

    Returns:
        dict[int, list]: Словарь форматов с номерами от 1, где:
            - format_id (str): Уникальный идентификатор формата.
            - ext (str): Расширение файла (например, "mp4").
            - width (int | None): Ширина видео или None (если аудиофайл).
            - height (int | None): Высота видео или None (если аудиофайл).
            - filesize (int | str): Размер файла в байтах или "Неизвестно".
            - tbr (float | str): Средний битрейт в кбит/с или "Неизвестно".
    """
    unique_formats = {}  # Храним уникальные видеоформаты
    best_audio = None  # Лучший аудиоформат
    audio_size = audio if isinstance(audio, (int, float)) else 0

    # Проходим по списку форматов и определяем лучший аудиоформат
    for f in formats:
        if f.get("vcodec") == "none" and f.get("abr") is not None:  # Это аудиофайл
            if best_audio is None or f.get("abr", 0) > best_audio.get("abr", 0):
                best_audio = f  # Запоминаем лучший аудиоформат

    # Фильтруем видеоформаты
    for f in formats:
        vcodec = f.get("vcodec", "")
        filesize = f.get("filesize", None)

        if vcodec.startswith(vcodec_prefix) and filesize:  # Проверяем видеокодек и размер
            resolution = f.get("resolution", f"{f.get('width', 'Неизвестно')}x{f.get('height', 'Неизвестно')}")

            if resolution not in unique_formats:  # Добавляем только уникальные разрешения
                total_size = filesize + audio_size  # Учитываем аудио
                unique_formats[resolution] = {
                    "format_id": f.get("format_id", "Неизвестно"),
                    "ext": f.get("ext", "Неизвестно"),
                    "width": f.get("width"),
                    "height": f.get("height"),
                    "filesize": total_size or "Неизвестно",
                    "tbr": f.get("tbr") or "Неизвестно"
                }

    # Формируем финальный словарь с номерами
    result = {}
    index = 1

    # Сначала добавляем аудио, если оно найдено
    if best_audio:
        result[index] = [{
            "format_id": best_audio.get("format_id", "Неизвестно"),
            "ext": best_audio.get("ext", "Неизвестно"),
            "width": None,
            "height": None,
            "filesize": best_audio.get("filesize") or "Неизвестно",
            "tbr": best_audio.get("tbr") or "Неизвестно"
        }]
        index += 1

    # Затем добавляем видеоформаты
    for resolution, format_data in unique_formats.items():
        result[index] = [format_data]
        index += 1
    return result

def main_kb(filtered_formats, audio_id, audio_size):
    """
    Формирует клавиатуру с кнопками для скачивания аудио и видео.

    Args:
        filtered_formats (dict[int, list]): Словарь списков форматов, где:
            - Ключ (int) — номер формата.
            - Значение (list[dict]) — список словарей с информацией о формате.
        audio_id (str): ID аудиофайла.
        audio_size (int): Размер аудиофайла в байтах.

    Returns:
        InlineKeyboardMarkup: Объект клавиатуры с кнопками загрузки.
    """
    button_list = []
    index = 1  # Начинаем нумерацию с 1

    # Добавляем кнопку для скачивания аудио с индексом 1
    size_text = f"{round(audio_size / (1024 ** 2), 2)} MB" if audio_size else "Неизвестно"
    button_list.append([
        InlineKeyboardButton(
            text=f" Cкачать {emoji.emojize(EMOJIS['sound'])} Аудио {emoji.emojize(EMOJIS['size'])} {size_text}",
            callback_data=f"yt_audio:{index}:{size_text}"
        )
    ])

    # Добавляем кнопки для видеоформатов, начиная с 2
    for format_list in filtered_formats.values():  # filtered_formats — это dict, где ключи не важны
        f = format_list[0]  # Берем первый элемент списка (основной формат)
        if f['ext'] == 'm4a' or f['ext'] == 'webm':  # Пропускаем m4a и webm
            continue

        size_text = f"{round(f['filesize'] / (1024 ** 2), 2)} MB" if isinstance(f['filesize'], (int, float)) else "Неизвестно"

        button_list.append([
            InlineKeyboardButton(
                text=f" Cкачать {emoji.emojize(EMOJIS['resolutions'])} {f['width']}x{f['height']} {emoji.emojize(EMOJIS['size'])} {size_text}",
                callback_data=f"yt_video:{index}:{size_text}"
            )
        ])
        index += 1  # Увеличиваем индекс

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