from data.models import Subscribe
from database import AsyncSessionLocal
from sqlalchemy.future import select


async def create_subscribe(user_id: int, channel_id: str):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            new_entry = Subscribe(
                user_id=user_id,
                channel_id=channel_id,
                status=True
            )
            session.add(new_entry)
        await session.commit()

async def update_subscribe_status(user_id: int, channel_id: str, status: bool):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            subscribe = await session.execute(
                select(Subscribe).filter_by(user_id=user_id, channel_id=channel_id)
            )
            subscribe = subscribe.scalar_one_or_none()
            if subscribe:
                subscribe.status = status
                await session.commit()

async def unsubscribe(user_id: int, channel_id: str):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            subscribe = await session.execute(
                select(Subscribe).filter_by(user_id=user_id, channel_id=channel_id)
            )
            subscribe = subscribe.scalar_one_or_none()
            if subscribe:
                subscribe.status = False
                await session.commit()

async def get_user_subscriptions(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Subscribe).filter_by(user_id=user_id, status=True)  # Только активные подписки
        )
        return result.scalars().all()