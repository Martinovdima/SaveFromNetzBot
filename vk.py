from yt_dlp import YoutubeDL
from typing import Tuple, Optional
import os
import asyncio

from sqlalchemy.orm import Session
from config import ffmpeg_path
from rest import DOWNLOAD_DIR


async def get_vk_video_info(url: str) -> Tuple[dict, str, str, str, Optional[int], str, str]:
    """
    Получает информацию о видео с VK с помощью yt-dlp.

    Args:
        url (str): Ссылка на видео.

    Returns:
        tuple: Кортеж, содержащий:
            - dict: Полная информация о видео.
            - str: Автор видео.
            - str: Ссылка на миниатюру (обложку).
            - str: ID видео.
            - int | None: Длительность видео в секундах или None, если не указано.
            - str: ID канала (если есть).
            - str: Дата загрузки в формате ГГГГММДД (если есть).
    """
    ydl_opts = {
        'quiet': True,
        'noplaylist': True,
        'extract_flat': False,
        'force_generic_extractor': False,  # Важно для корректной работы с VK
    }

    with YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as e:
            raise RuntimeError(f"Не удалось получить информацию о видео: {e}")

    duration = info.get('duration')
    author = info.get('uploader', 'Неизвестно')
    thumbnail_url = info.get('thumbnail', 'Нет обложки')
    video_id = info.get('id', 'Неизвестно')
    channel_id = info.get('uploader_id', 'Неизвестно')
    upload_date = info.get('upload_date', 'Нет данных')

    return info, author, thumbnail_url, video_id, duration, channel_id, upload_date


async def get_formats_vk_video(video_info):
    """
    Возвращает список уникальных видео- и аудио-форматов с рассчитанным размером, если возможно.

    Args:
        video_info (dict): Информация о видео, полученная через yt-dlp.

    Returns:
        List[Dict]: Список форматов. Каждый формат — словарь с ключами:
            - format_id (str)
            - resolution (str, например '640x360')
            - filesize (str) — в МБ или "Неизвестно"
    """
    formats = video_info.get("formats", [])
    duration = video_info.get("duration")  # В секундах

    result = []
    seen_resolutions = set()
    best_audio = None

    # Карта соответствия высоты к ширине (ориентировочно, можно расширять)
    height_to_width = {
        144: 256,
        240: 426,
        360: 640,
        480: 854,
        720: 1280,
        1080: 1920,
    }

    # Найти лучший аудиоформат
    for f in formats:
        if f.get("vcodec") == "none" and f.get("ext") == "m4a":
            if not best_audio or (f.get("abr", 0) > best_audio.get("abr", 0)):
                best_audio = f

    if best_audio:
        tbr = best_audio.get("tbr")
        file_size = (tbr * duration) / (8 * 1024) if tbr and duration else None
        size_text = f"{round(file_size, 2)} MB" if file_size else "Неизвестно"

        result.append({
            "format_id": best_audio.get("format_id", "Неизвестно"),
            "resolution": "audio",
            "filesize": size_text
        })

    # Обработка видеоформатов
    for f in formats:
        if f.get("vcodec") != "none":
            width = f.get("width")
            height = f.get("height")

            # Приоритет: width + height -> resolution (360p и т.п.) -> пропустить
            if width and height:
                resolution = f"{width}x{height}"
            elif f.get("resolution") and 'p' in f.get("resolution"):
                try:
                    res_height = int(f["resolution"].replace("p", ""))
                    inferred_width = height_to_width.get(res_height, None)
                    if inferred_width:
                        resolution = f"{inferred_width}x{res_height}"
                    else:
                        continue  # Неизвестное разрешение — пропускаем
                except ValueError:
                    continue
            else:
                continue  # Никакой инфы — пропускаем

            if resolution in seen_resolutions:
                continue
            seen_resolutions.add(resolution)

            file_size = f.get("filesize")
            if not file_size and f.get("tbr") and duration:
                file_size = (f["tbr"] * duration) / (8 * 1024)  # в МБ

            size_text = f"{round(file_size, 2)} MB" if isinstance(file_size, (int, float)) else "Неизвестно"

            result.append({
                "format_id": f.get("format_id", "Неизвестно"),
                "resolution": resolution,
                "filesize": size_text
            })

    return result


async def download_vk_video_async(video, format_id):
    """
    Асинхронно загружает видео с VK с помощью yt-dlp.

    Args:
        db (Session): Сессия базы данных для получения данных пользователя.
        user_id (int): ID пользователя, который запросил скачивание.
        format_id (str): Идентификатор формата видео.

    Returns:
        tuple[str, dict] | None:
            - str: Путь к загруженному файлу.
            - dict: Информация о видео из yt-dlp.
            - None, если произошла ошибка.
    """

    def sync_download():
        ffmpeg_path = os.path.abspath("ffmpeg/bin/ffmpeg.exe")
        os.environ["PATH"] += os.pathsep + os.path.dirname(ffmpeg_path)
        url = video.url
        title = video.name
        video_id = video.id


        ydl_opts = {
            'format': f'{format_id}+ba/best',
            'outtmpl': os.path.join(DOWNLOAD_DIR, f"{title}_{video_id}.%(ext)s"),
            'merge_output_format': 'mp4',
            'quiet': True,
            'noplaylist': True,
            'http_chunk_size': 2097152,  # 2MB
            'concurrent-fragments': 15,  # 10 потоков
            'ffmpeg_location': '/usr/bin/ffmpeg',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Referer': 'https://vk.com',
            },
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)  # Скачиваем видео
                ext = info.get('ext', 'mp4')  # Определяем расширение файла
                file_path = os.path.join(DOWNLOAD_DIR, f"{title}_{video_id}.{ext}")
                return file_path, info if os.path.exists(file_path) else None
        except Exception as e:
            print(f"Ошибка при скачивании: {e}")
            return None

    # Запускаем синхронную загрузку в отдельном потоке
    return await asyncio.to_thread(sync_download)


