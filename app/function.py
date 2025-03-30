from aiogram.types import InlineQueryResultArticle, InlineQueryResultVideo, InputTextMessageContent
from googleapiclient.discovery import build
from config import YOUTUBE_API_KEY



# Инициализация API клиента
api_key =  YOUTUBE_API_KEY
youtube = build("youtube", "v3", developerKey=api_key)


async def search_youtube(query, offset=""):
    try:
        # Запрашиваем каналы сначала
        search_response_channels = youtube.search().list(
            q=query,
            part="id,snippet",
            maxResults=1,  # Каналы в приоритете, но ограничим количество
            type="channel",
            pageToken=offset if offset else None
        ).execute()

        # Запрашиваем видео
        search_response_videos = youtube.search().list(
            q=query,
            part="id,snippet",
            maxResults=45,  # Видео берём больше, но они идут после каналов
            type="video",
            pageToken=offset if offset else None
        ).execute()

        results = []
        next_page_token = search_response_videos.get("nextPageToken", "")

        # Добавляем каналы ПЕРВЫМИ в список
        for item in search_response_channels.get("items", []):
            channel_id = item["id"]["channelId"]
            title = item["snippet"]["title"]
            thumbnail = item["snippet"]["thumbnails"]["high"]["url"]

            results.append(
                InlineQueryResultArticle(
                    id=channel_id,
                    title=f"📺 {title}",
                    url=f"https://www.youtube.com/channel/{channel_id}",
                    thumb_url=thumbnail,
                    description="YouTube канал",
                    input_message_content=InputTextMessageContent(
                        message_text=f"https://www.youtube.com/channel/{channel_id}"
                    )
                )
            )

        # Добавляем видео (отфильтровав Shorts)
        for item in search_response_videos.get("items", []):
            video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            description = item["snippet"].get("description", "Нет описания")
            thumbnail = item["snippet"]["thumbnails"]["high"]["url"]

            # Фильтруем Shorts (по ключевому слову "Shorts" или отсутствию описания)
            if "shorts" in title.lower() or description == "Нет описания":
                continue

            results.append(
                InlineQueryResultVideo(
                    id=video_id,
                    title=title,
                    video_url=f"https://www.youtube.com/watch?v={video_id}",
                    mime_type="video/mp4",
                    thumbnail_url=thumbnail,
                    description=description,
                    input_message_content=InputTextMessageContent(
                        message_text=f"https://www.youtube.com/watch?v={video_id}"
                    )
                )
            )

        return results, next_page_token

    except Exception as e:
        print(f"Ошибка при запросе к YouTube API: {e}")
        return [], ""


async def get_channel_videos(channel_id):
    try:
        # Получаем информацию о канале
        request = youtube.channels().list(
            part="snippet,contentDetails,statistics",
            id=channel_id
        )
        response = request.execute()

        if not response.get("items"):
            return None, "Канал не найден"

        channel = response["items"][0]
        channel_name = channel["snippet"]["title"]
        channel_avatar = channel["snippet"]["thumbnails"]["high"]["url"]
        subscribers_count = format_number(channel["statistics"].get("subscriberCount", 0))
        video_count = format_number(channel["statistics"].get("videoCount", 0))

        # Получаем плейлист с загруженными видео
        uploads_playlist_id = channel["contentDetails"]["relatedPlaylists"]["uploads"]

        # Получаем список видео
        videos = []
        next_page_token = None

        while True:
            playlist_request = youtube.playlistItems().list(
                part="snippet",
                playlistId=uploads_playlist_id,
                maxResults=50,
                pageToken=next_page_token if next_page_token else None
            )
            playlist_response = playlist_request.execute()

            for item in playlist_response.get("items", []):
                video_id = item["snippet"]["resourceId"]["videoId"]
                title = item["snippet"]["title"]
                thumbnail = item["snippet"]["thumbnails"]["high"]["url"]

                videos.append({
                    "id": video_id,
                    "title": title,
                    "thumbnail": thumbnail,
                    "url": f"https://www.youtube.com/watch?v={video_id}"
                })

            next_page_token = playlist_response.get("nextPageToken")
            if not next_page_token:
                break  # Если видео закончились — выходим

        return {
            "channel_name": channel_name,
            "channel_avatar": channel_avatar,
            "subscribers": subscribers_count,
            "video_count": video_count,
            "videos": videos
        }

    except Exception as e:
        print(f"Ошибка при получении видео канала: {e}")
        return None


async def get_channel_info(url: str):
    # Извлекаем ID канала из URL
    channel_id = None
    if "youtube.com/channel/" in url:
        # Пример: https://www.youtube.com/channel/UC1234567890abcdef
        channel_id = url.split("youtube.com/channel/")[-1]
    elif "youtube.com/c/" in url:
        # Пример: https://www.youtube.com/c/YourChannelName
        channel_name = url.split("youtube.com/c/")[-1]
        # Запрашиваем канал по имени
        request = youtube.channels().list(part="id", forUsername=channel_name)
        response = request.execute()
        if response.get("items"):
            channel_id = response["items"][0]["id"]

    if not channel_id:
        return "Не удалось извлечь ID канала"

    # Запрос к YouTube API для получения информации о канале
    request = youtube.channels().list(
        part="snippet,contentDetails,statistics",
        id=channel_id
    )
    response = request.execute()

    # Обработка ответа от API
    if response.get("items"):
        channel = response["items"][0]
        channel_name = channel["snippet"]["title"]
        channel_avatar = channel["snippet"]["thumbnails"]["high"]["url"]
        subscribers_count = channel["statistics"].get("subscriberCount", "Неизвестно")
        video_count = channel["statistics"].get("videoCount", "Неизвестно")

        format_subscribe_count = await format_number(subscribers_count)

        return channel_id, channel_name, channel_avatar, format_subscribe_count, video_count
    else:
        return "Не удалось получить информацию о канале"


async def format_number(value: int) -> str:
    value = int(value)  # Убеждаемся, что это число
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f} млн"
    elif value >= 1_000:
        return f"{value / 1_000:.1f} тыс"
    return str(value)