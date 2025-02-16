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
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)  # Только получаем данные, без скачивания


    duration = info.get('duration', None)
    if duration:
        minutes = duration // 60
        seconds = duration % 60

    video_id = info.get("id", "Неизвестно")
    # 3. Получаем имя автора
    author = info.get("uploader", "Неизвестно")

    # 4. Получаем обложку видео (URL картинки)
    thumbnail_url = info.get("thumbnail", "Неизвестно")

    return info, author, thumbnail_url, video_id, duration

def get_format_inst_video(video_info):
    formats = video_info.get("formats", [])
    unique_resolutions = {}  # Словарь для хранения уникальных форматов
    best_audio = None

    # Поиск лучшего аудио (с наибольшим abr)
    for f in formats:
        if f.get("vcodec") == "none":
            if best_audio is None or f.get("abr", 0) > best_audio.get("abr", 0):
                best_audio = f

    result = []

    # Добавляем только один лучший аудиоформат, если найден
    if best_audio:
        result.append({
            "format_id": best_audio.get("format_id", "Неизвестно"),
            "ext": best_audio.get("ext", "Неизвестно"),
            "width": None,
            "height": None,
            "filesize": best_audio.get("filesize") or "Неизвестно",
            "tbr": best_audio.get("tbr") or "Неизвестно"
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
                    "filesize": f.get("filesize") or "Неизвестно",
                    "tbr": f.get("tbr") or "Неизвестно"
                }

    # Добавляем в итоговый список только уникальные видео-форматы
    result.extend(unique_resolutions.values())

    return result


def main_kb_inst(formats, duration):
    button_list = []
    added_audio = False  # Флаг, чтобы не добавлять аудио несколько раз
    size_audio_file = 0

    for f in formats:
        resolution_text = "Аудио" if f.get("width") is None else f"{f.get('width', 'Неизвестно')}x{f.get('height', 'Неизвестно')}"

        # Проверяем, есть ли 'vbr' и 'duration'
        if 'tbr' in f and isinstance(f['tbr'], (int, float)) and duration:
            # Рассчитываем размер файла
            file_size = (f['tbr'] * duration) / (8 * 1024)  # в МБ
            size_text = f"{round(file_size, 2)} MB"
        else:
            # Если данных недостаточно, выводим "Неизвестно"
            size_text = "Неизвестно"

        if resolution_text == "Аудио":
            size_audio_file = file_size
            if not added_audio:  # Добавляем аудио только один раз
                button_list.append([
                    InlineKeyboardButton(
                        text=f"Скачать {emoji.emojize(EMOJIS['sound'])} {resolution_text} {emoji.emojize(EMOJIS['size'])} {size_text}",
                        callback_data=f"inst_download_audio:{f.get('format_id', 'Неизвестно')}:{size_text}"
                    )
                ])
                added_audio = True  # Помечаем, что аудио уже добавлено
        else:
            button_list.append([
                InlineKeyboardButton(
                    text=f"Скачать {emoji.emojize(EMOJIS['resolutions'])} {resolution_text} {emoji.emojize(EMOJIS['size'])} {size_text}",
                    callback_data=f"inst_download:{f.get('format_id', 'Неизвестно')}:{size_text}"
                )
            ])

    return InlineKeyboardMarkup(inline_keyboard=button_list)

def download_inst_video(db: Session, user_id: int, format_id):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user or not user.url:
        raise ValueError("Ссылка не найдена в базе данных. Отправьте её ещё раз.")

    url = user.url
    title = user.title
    video_id = user.video_id

    ydl_opts = {
        'format': f'{format_id}+ba/best',  # Выбирает лучшее видео+аудио
        'outtmpl': os.path.join(DOWNLOAD_DIR, f"{title}_%(resolution)s{video_id}.%(ext)s"),  # Формат имени файла
        'merge_output_format': 'mp4',  # Принудительное объединение в MP4
        'quiet': False,  # Выводит процесс загрузки
        'noplaylist': True,  # Загружает только одно видео
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)  # Загружаем видео
            ext = info.get('ext', 'mp4')  # Если не найдено расширение, по умолчанию 'mkv'
            resolution = info.get('resolution', 'unknow')
            file_path = os.path.join(DOWNLOAD_DIR, f"{title}_{resolution}{video_id}.{ext}")
            return file_path, info if os.path.exists(file_path) else None
    except Exception as e:
        print(f"Ошибка при скачивании: {e}")
        return None


