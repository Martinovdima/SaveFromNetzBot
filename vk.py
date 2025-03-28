from yt_dlp import YoutubeDL
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import emoji
import os
import asyncio

from sqlalchemy.orm import Session
from db import User
from rest import EMOJIS, DOWNLOAD_DIR


def get_vk_video_info(url):
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
        """
    ydl_opts = {
        'quiet': True,  # Отключает лишние логи
        'noplaylist': True,  # Загружает только одно видео
        'extract_flat': False,  # Позволяет получить детали о видео
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)  # Только получаем данные, без скачивания


    duration = info.get('duration', None)
    duration = info.get('duration', None)
    video_id = info.get("id", "Неизвестно")
    author = info.get("uploader", "Неизвестно")
    thumbnail_url = info.get("thumbnail", "Неизвестно")

    return info, author, thumbnail_url, video_id, duration


def get_formats_vk_video(video_info):
    """
        Извлекает и фильтрует доступные форматы видео и аудио из информации о видео VK.

        Args:
            video_info (dict): Словарь с информацией о видео, полученный из yt-dlp.

        Returns:
            dict[int, list]: Словарь форматов с номерами от 1, где:
                - format_id (str): Уникальный идентификатор формата.
                - ext (str): Расширение файла (например, "mp4").
                - width (int | None): Ширина видео или None (если аудиофайл).
                - height (int | None): Высота видео или None (если аудиофайл).
                - filesize (int | str): Размер файла в байтах или "Неизвестно".
                - tbr (float | str): Средний битрейт в кбит/с или "Неизвестно".
        """
    formats = video_info.get("formats", [])
    unique_resolutions = {}  # Словарь для хранения уникальных форматов
    best_audio = None

    # Находим лучший аудиоформат (наибольший abr)
    for f in formats:
        if f.get("vcodec") == "none" and f.get("ext") == "m4a":  # Только аудио форматы M4A
            f_abr = f.get("abr") or 0  # Если abr отсутствует, заменяем на 0
            best_audio_abr = best_audio.get("abr", 0) if best_audio else 0

            if best_audio is None or f_abr > best_audio_abr:
                best_audio = f  # Запоминаем лучший аудиоформат

    # Обрабатываем видео-форматы, уникализируя их по `resolution`
    for f in formats:
        if f.get("vcodec") != "none" and f.get('width') != None:  # Исключаем аудио
            resolution = f.get("resolution", f"{f.get('width', 'Неизвестно')}x{f.get('height', 'Неизвестно')}")

            if resolution not in unique_resolutions:  # Уникализируем по разрешению
                unique_resolutions[resolution] = {
                    "format_id": f.get("format_id", "Неизвестно"),
                    "ext": f.get("ext", "Неизвестно"),
                    "width": f.get("width"),
                    "height": f.get("height"),
                    "filesize": f.get("filesize") or "Неизвестно",
                    "tbr": f.get("tbr") or "Неизвестно"
                }

    # Формируем итоговый список с нумерацией
    result = {}
    index = 1

    # Добавляем лучший аудиоформат (если найден)
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

    # Добавляем видео-форматы
    for video_format in unique_resolutions.values():
        result[index] = [video_format]
        index += 1
    return result


async def download_vk_video_async(db: Session, user_id: int, format_id):
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
        ffmpeg_path = os.path.abspath("/usr/bin/ffmpeg")
        os.environ["PATH"] += os.pathsep + os.path.dirname(ffmpeg_path)
        """Синхронная функция для скачивания видео (запускается в отдельном потоке)."""
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user or not user.url:
            raise ValueError("Ссылка не найдена в базе данных. Отправьте её ещё раз.")


        url = user.url
        title = user.title
        video_id = user.video_id

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

def get_format_id_from_callback(callback_data, formats_dict):
    """
    Получает format_id из callback_data, используя словарь форматов.

    Args:
        callback_data (str): Данные callback в формате "vk_audio:номер:размер".
        formats_dict (dict[int, list]): Словарь форматов, где ключ — номер формата.

    Returns:
        str: format_id соответствующего формата или "Неизвестно", если не найден.
    """
    try:
        format_number = int(callback_data.split(":")[1])  # Извлекаем номер формата
        format_info = formats_dict.get(format_number)  # Получаем список с инфо

        if format_info:
            return format_info[0].get("format_id", "Неизвестно")  # Возвращаем format_id
    except (IndexError, ValueError):
        pass  # Если callback_data невалидный, просто возвращаем "Неизвестно"

    return "Неизвестно"
