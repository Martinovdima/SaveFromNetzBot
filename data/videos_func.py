from data.models import Video
from database import AsyncSessionLocal
from sqlalchemy.future import select


async def create_video(youtube_id: str, name: str, author: str, url: str, channel_id: str, time: str = None,
                       date: str = None):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Проверяем, есть ли уже видео с таким URL
            result = await session.execute(select(Video).filter(Video.url == url))
            existing_video = result.scalars().first()

            if existing_video:
                return existing_video.id  # Если видео есть, возвращаем его ID

            # Если видео нет, создаём новую запись
            new_video = Video(
                youtube_id=youtube_id,
                name=name,
                author=author,
                url=url,
                channel_id=channel_id,
                time=time,
                date=date
            )
            session.add(new_video)
            await session.flush()  # Фиксируем ID нового объекта перед коммитом

        await session.commit()
        return new_video.id  # Возвращаем ID нового видео
async def update_video_thumbnail(video_id: int, telegram_photo_id: str):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(Video).where(Video.id == video_id))
            video = result.scalars().first()

            if not video:
                return False  # Видео не найдено

            video.thumbnail = telegram_photo_id
            await session.commit()
            return True  # Успешное обновление
async def get_video_by_url(url: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Video).where(Video.url == url))
        return result.scalars().first()
async def is_video_in_db(url: str) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Video).where(Video.url == url))
        return result.scalars().first() is not None
async def get_video_by_youtube_id(youtube_id: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Video).where(Video.youtube_id == youtube_id))
        return result.scalars().first()
async def get_video(video_id: int):
    async with AsyncSessionLocal() as session:  # ✅ Используем async with
        result = await session.execute(select(Video).where(Video.id == video_id))  # ✅ Добавили await
        video = result.scalars().first()
        return video