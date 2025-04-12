from data.models import Playlist
from database import AsyncSessionLocal
from sqlalchemy.future import select


async def create_playlist(user_id: int, name: str):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            new_playlist = Playlist(user_id=user_id, name=name)
            session.add(new_playlist)
        await session.commit()

async def delete_playlist(playlist_id: int):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            playlist = await session.get(Playlist, playlist_id)
            if playlist:
                await session.delete(playlist)
        await session.commit()

async def get_playlists_by_user(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Playlist).where(Playlist.user_id == user_id)
        )
        return result.scalars().all()

async def get_playlist_by_name(user_id: int, name: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Playlist).where(Playlist.user_id == user_id, Playlist.name == name)
        )
        return result.scalar_one_or_none()

async def get_last_playlist(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Playlist)
            .where(Playlist.user_id == user_id)
            .order_by(Playlist.id.desc())  # Сортируем по убыванию ID
        )
        return result.scalar_one_or_none()