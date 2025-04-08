from rest import DOWNLOAD_DIR, EMOJIS
from yt_dlp import YoutubeDL
import asyncio
import emoji
import os


async def get_tiktok_video_info(url):
    ydl_opts = {
        'quiet': True,  # Отключает лишние логи
        'noplaylist': True,  # Загружает только одно видео
        'extract_flat': False,  # Позволяет получить детали о видео
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)  # Только получаем данные, без скачивания
        video_id = info.get("id", "Неизвестно")
        title = info.get("title", "Без названия")
        author = (info.get("uploader") if info.get("uploader") != "Неизвестно" else info.get("uploader_id", "Неизвестно"))
        channel_id = info.get("channel_id", "Неизвестно")
        duration = info.get("duration", 0)
        upload_date = info.get("upload_date", "Нет данных")
        thumbnail_url = info.get("thumbnail", "Неизвестно")

    return info, video_id, title, author, channel_id, duration, upload_date, thumbnail_url

async def download_tiktok_video(video, format_id):
    def sync_download():
        url = video.url
        title = video.name
        video_id = video.id

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
                resolution = info.get('resolution', 'unknow')
                ext = info.get('ext', 'mp4')  # Если не найдено расширение, по умолчанию 'mkv'
                file_path = os.path.join(DOWNLOAD_DIR, f"{title}_{resolution}{video_id}.{ext}")
                return file_path, info if os.path.exists(file_path) else None
        except Exception as e:
            print(f"Ошибка при скачивании: {e}")
            return None
    # Запускаем синхронную загрузку в отдельном потоке
    return await asyncio.to_thread(sync_download)

async def get_tiktok_video_details(info):
    """Возвращает список словарей с форматами видео, исключая дубликаты разрешений"""

    formats = {}

    if "formats" in info:
        for fmt in info["formats"]:
            if fmt.get("vcodec") != "none":  # Только видео
                format_id = fmt.get("format_id", "Неизвестно")
                resolution = f"{fmt['width']}x{fmt['height']}" if fmt.get("width") and fmt.get(
                    "height") else "Неизвестно"
                size_mb = round(fmt.get("filesize", 0) / (1024 * 1024), 2) if fmt.get("filesize") else 0

                # Сохраняем только самый большой формат для каждого разрешения
                if resolution not in formats or size_mb > formats[resolution][1]:
                    formats[resolution] = (format_id, size_mb)

    # Преобразуем в список словарей
    result = [{"format_id": fmt_id, "resolution": res, "filesize": size} for res, (fmt_id, size) in formats.items()]

    return result

async def create_caption(video_info, format_id):
    """Создает описание (caption) для видео, используя данные из video_info"""
    formatted_duration = video_info.get('duration', 0)

    # Ищем нужный формат по format_id
    selected_format = None
    if "formats" in video_info:
        for fmt in video_info["formats"]:
            if fmt.get("vcodec") != "none" and fmt.get("format_id") == format_id:  # Только видео
                selected_format = fmt
                break

    # Извлекаем информацию о разрешении и размере файла
    if selected_format:
        best_resolution = f"{selected_format.get('width', 'Неизвестно')}x{selected_format.get('height', 'Неизвестно')}" \
            if selected_format.get("width") and selected_format.get("height") else "Неизвестно"
        filesize_mb = round(selected_format.get("filesize", 0) / (1024 * 1024), 2) if selected_format.get("filesize") else "Неизвестно"
    else:
        best_resolution = "Неизвестно"
        filesize_mb = "Неизвестно"

    # Формируем caption
    caption = (
        f"{emoji.emojize(EMOJIS['title'])} Название: {video_info.get('title', 'Неизвестно')}\n"
        f"{emoji.emojize(EMOJIS['autor'])} Автор: {video_info.get('uploader', 'Неизвестно')}\n"
        f'\n'
        f"{emoji.emojize(EMOJIS['view'])} Просмотры: {video_info.get('view_count', 'Неизвестно')}\n"
        f"{emoji.emojize(EMOJIS['durations'])} Длительность: {formatted_duration} сек\n"
        f'\n'
        f"{emoji.emojize(EMOJIS['resolutions'])} Разрешение: {best_resolution}\n"
        f"{emoji.emojize(EMOJIS['size'])} Размер файла: {filesize_mb} МБ\n"
    )

    return caption