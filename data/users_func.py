from data.models import User
from database import AsyncSessionLocal
from sqlalchemy.future import select
from datetime import datetime

async def create_user(telegram_id: int, username: str, api: str):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Проверяем, есть ли уже пользователь с таким telegram_id
            result = await session.execute(
                select(User).filter(User.telegram_id == telegram_id)
            )
            existing_user = result.scalars().first()

            if existing_user:
                # Если пользователь существует, обновляем поле last_enter_date
                existing_user.last_enter_date = datetime.utcnow()
                # Возвращаем ID существующего пользователя
                user_id = existing_user.telegram_id
            else:
                # Если пользователя нет, создаём нового
                new_entry = User(
                    telegram_id=telegram_id,
                    username=username,
                    api=api,
                    login_time=datetime.utcnow(),
                    last_enter_date=datetime.utcnow()
                )
                session.add(new_entry)
                await session.commit()  # Коммитим добавление нового пользователя
                # Возвращаем ID нового пользователя
                user_id = new_entry.telegram_id

        return user_id  # Возвращаем ID пользователя, который был либо создан, либо обновлен

async def get_user(telegram_id: int):
    async with AsyncSessionLocal() as session:
        return await session.get(User, telegram_id)

async def increment_tt_count(telegram_id: int):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

            if user:
                # Если yt_count ещё не установлен — начинаем с 1
                user.tt_count = (user.tt_count or 0) + 1
                session.add(user)
            else:
                # Если пользователя нет, можно создать нового
                new_user = User(
                    telegram_id=telegram_id,
                    tt_count=1
                )
                session.add(new_user)

        await session.commit()

async def increment_vk_count(telegram_id: int):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

            if user:
                # Если yt_count ещё не установлен — начинаем с 1
                user.vk_count = (user.vk_count or 0) + 1
                session.add(user)
            else:
                # Если пользователя нет, можно создать нового
                new_user = User(
                    telegram_id=telegram_id,
                    vk_count=1
                )
                session.add(new_user)

        await session.commit()

async def increment_yt_count(telegram_id: int):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

            if user:
                # Если yt_count ещё не установлен — начинаем с 1
                user.yt_count = (user.yt_count or 0) + 1
                session.add(user)
            else:
                # Если пользователя нет, можно создать нового
                new_user = User(
                    telegram_id=telegram_id,
                    yt_count=1
                )
                session.add(new_user)

        await session.commit()

async def last_enter(telegram_id: int):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            user = await session.get(User, telegram_id)
            if user:
                user.last_enter_date = datetime.utcnow()
                await session.commit()

