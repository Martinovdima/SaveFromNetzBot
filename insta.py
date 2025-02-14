from yt_dlp import YoutubeDL
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import emoji
import os

from sqlalchemy.orm import Session
from db import User
from rest import EMOJIS, DOWNLOAD_DIR

def get_insta_video_info(url):
    ydl_opts = {
        'quiet': True,  # Отключает лишние логи
        'noplaylist': True,  # Загружает только одно видео
        'extract_flat': False,  # Позволяет получить детали о видео
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)  # Только получаем данные, без скачивания
    # 2. Получаем ID
    video_id = info.get("id", "Неизвестно")

    # 3. Получаем имя автора
    author = info.get("uploader", "Неизвестно")

    # 4. Получаем обложку видео (URL картинки)
    thumbnail_url = info.get("thumbnail", "Неизвестно")

    return info, video_id, author, thumbnail_url

def get_format_inst_video(video_info):
    formats = video_info.get("formats", [])
    unique_resolutions = {}  # Словарь для хранения уникальных форматов

    # Добавляем аудио-формат в начало списка (если есть)
    audio_format = next((f for f in formats if f.get("vcodec") == "none"), None)
    result = []

    if audio_format:
        result.append({
            "format_id": audio_format.get("format_id", "Неизвестно"),
            "ext": audio_format.get("ext", "Неизвестно"),
            "width": None,
            "height": None,
            "filesize": audio_format.get("filesize") or audio_format.get("filesize_approx", "Неизвестно")
        })

    # Обрабатываем видео-форматы, уникализируя их по `resolution`
    for f in formats:
        if f.get("vcodec") != "none":  # Исключаем аудио
            resolution = f.get("resolution", f"{f.get('width', 'Неизвестно')}x{f.get('height', 'Неизвестно')}")
            if resolution not in unique_resolutions:  # Уникализируем
                unique_resolutions[resolution] = {
                    "format_id": f.get("format_id", "Неизвестно"),
                    "ext": f.get("ext", "Неизвестно"),
                    "width": f.get("width"),
                    "height": f.get("height"),
                    "filesize": f.get("filesize") or f.get("filesize_approx", "Неизвестно")
                }

    # Добавляем в итоговый список
    result.extend(unique_resolutions.values())

    return result

def main_kb_inst(formats):
    button_list = []

    for f in formats:
        # Определяем текст кнопки
        resolution_text = "Аудио" if f["width"] is None else f"{f['width']}x{f['height']}"
        size_text = f"{round(f['filesize'] / (1024 * 1024), 2)} MB" if isinstance(f["filesize"], int) else "Неизвестно"
        if resolution_text == "Аудио":
            button_list.append([
                InlineKeyboardButton(
                    text=f"Скачать {emoji.emojize(EMOJIS['resolutions'])} {resolution_text} {emoji.emojize(EMOJIS['size'])} {size_text}",
                    callback_data=f"inst_download_audio:{f['format_id']}"
                )])
        else:
            button_list.append([
                InlineKeyboardButton(
                    text=f"Скачать {resolution_text} | {size_text}",
                    callback_data=f"inst_download:{f['format_id']}"
                )
            ])

    # Создаем клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=button_list)
    return keyboard

def download_inst_video(db: Session, user_id: int, format_id):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user or not user.url:
        raise ValueError("Ссылка не найдена в базе данных. Отправьте её ещё раз.")

    url = user.url
    title = user.title
    video_id = user.video_id

    ydl_opts = {
        'format': f'{format_id}+ba/best',  # Выбирает лучшее видео+аудио
        'outtmpl': os.path.join(DOWNLOAD_DIR, f'{title}{video_id}.%(ext)s'),  # Формат имени файла
        'merge_output_format': 'mp4',  # Принудительное объединение в MP4
        'quiet': False,  # Выводит процесс загрузки
        'noplaylist': True,  # Загружает только одно видео
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)  # Загружаем видео
            ext = info.get('ext', 'mp4')  # Если не найдено расширение, по умолчанию 'mkv'
            file_path = os.path.join(DOWNLOAD_DIR, f"{title}{video_id}.{ext}")
            return file_path, info if os.path.exists(file_path) else None
    except Exception as e:
        print(f"Ошибка при скачивании: {e}")
        return None