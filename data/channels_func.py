from data.models import Channel
from database import AsyncSessionLocal
from sqlalchemy.future import select

async def create_or_update_channel(
    channel_id: int,
    channel_name: str = None,
    channel_avatar: str = None,
    subscribers_count: str = None,
    video_count: str = None
):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(Channel).filter(Channel.channel_id == str(channel_id))
            )
            channel = result.scalars().first()

            if channel:
                # Обновляем только те поля, которые были переданы
                if channel_name is not None:
                    channel.channel_name = channel_name
                if channel_avatar is not None:
                    channel.channel_avatar = channel_avatar
                if subscribers_count is not None:
                    channel.subscribers_count = subscribers_count
                if video_count is not None:
                    channel.video_count = video_count
            else:
                # Создаём новый канал
                channel = Channel(
                    channel_id=str(channel_id),
                    channel_name=channel_name,
                    channel_avatar=channel_avatar,
                    subscribers_count=subscribers_count,
                    video_count=video_count
                )
                session.add(channel)

        await session.commit()
        return channel.channel_id