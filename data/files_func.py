from data.models import File
from database import AsyncSessionLocal
from sqlalchemy.future import select


async def create_file(video_id: int, format_id: int, playlist_id: int = None, id_telegram: str = None):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Проверяем, есть ли уже файл с таким video_id и format_id
            result = await session.execute(
                select(File).filter(File.video_id == video_id, File.format_id == format_id)
            )
            existing_file = result.scalars().first()

            if existing_file:
                return existing_file.id_telegram  # Если файл есть, возвращаем его id_telegram

            # Если файла нет, создаём новую запись
            new_file = File(
                video_id=video_id,
                format_id=format_id,
                playlist_id=playlist_id,
                id_telegram=id_telegram
            )
            session.add(new_file)
            await session.flush()  # Фиксируем ID нового объекта перед коммитом

        await session.commit()
        return new_file.id_telegram  # Возвращаем id_telegram нового файла
async def add_file_to_playlist(file_id: int, playlist_id: int):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            file = await session.get(File, file_id)
            if file:
                file.playlist_id = playlist_id
        await session.commit()
async def delete_file(file_id: int):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            file = await session.get(File, file_id)
            if file:
                await session.delete(file)
        await session.commit()
async def get_file(file_id: int):
    async with AsyncSessionLocal() as session:
        return await session.get(File, file_id)
async def get_telegram_id_by_format_id(format_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(File.id_telegram).where(File.format_id == format_id)
        )
        telegram_id = result.scalar_one_or_none()  # Получаем единственное значение или None
        return telegram_id  # Вернет id_telegram или None, если записи нет