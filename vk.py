from yt_dlp import YoutubeDL
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import emoji
import os

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
        list[dict]: Список форматов с полями:
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

def make_keyboard_vk(formats, duration):
    """
        Создаёт клавиатуру с кнопками для скачивания аудио и видео из VK.

        Args:
            formats (list[dict]): Список форматов видео и аудио, полученный из yt-dlp.
            duration (int | None): Длительность видео в секундах или None, если неизвестно.

        Returns:
            InlineKeyboardMarkup: Объект клавиатуры с кнопками загрузки.
        """
    button_list = []
    added_audio = False  # Флаг, чтобы не добавлять аудио несколько раз

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
            if not added_audio:  # Добавляем аудио только один раз
                button_list.append([
                    InlineKeyboardButton(
                        text=f"Скачать {emoji.emojize(EMOJIS['sound'])} {resolution_text} {emoji.emojize(EMOJIS['size'])} {size_text}",
                        callback_data=f"vk_download_audio:{f.get('format_id', 'Неизвестно')}:{size_text}"
                    )
                ])
                added_audio = True  # Помечаем, что аудио уже добавлено
        else:
            button_list.append([
                InlineKeyboardButton(
                    text=f"Скачать {emoji.emojize(EMOJIS['resolutions'])} {resolution_text} {emoji.emojize(EMOJIS['size'])} {size_text}",
                    callback_data=f"vk_download_video:{f.get('format_id', 'Неизвестно')}:{size_text}"
                )
            ])

    return InlineKeyboardMarkup(inline_keyboard=button_list)

def download_vk_video(db: Session, user_id: int, format_id):
    """
    Загружает видео с VK по сохранённой ссылке пользователя.

    Args:
        db (Session): Сессия базы данных для получения данных пользователя.
        user_id (int): ID пользователя, который запросил скачивание.
        format_id (str): Идентификатор формата видео.

    Returns:
        tuple[str, dict] | None: Кортеж из:
            - str: Путь к загруженному файлу.
            - dict: Информация о видео из yt-dlp.
            Возвращает None в случае ошибки или если файл не найден.

    """
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


