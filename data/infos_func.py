from data.models import Info
from database import AsyncSessionLocal
from sqlalchemy.future import select
import re


async def create_info(video_id: int, format_id: str, type: str = 'Video', resolution: str = None, size: str = None, status: bool = False):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Проверяем, есть ли уже такой объект Info
            result = await session.execute(
                select(Info).filter(Info.video_id == video_id, Info.format_id == format_id)
            )
            existing_info = result.scalars().first()

            if existing_info:
                return existing_info  # Если объект найден, возвращаем его

            # Если объект не найден, создаём новый
            new_info = Info(
                video_id=video_id,
                format_id=format_id,
                type=type,
                resolution=resolution,
                size=size,
                status=status
            )
            session.add(new_info)
            await session.flush()  # Фиксируем новый объект перед коммитом

        await session.commit()
async def get_info_by_video_id(video_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Info).where(Info.video_id == video_id))
        return result.scalars().all()
async def get_status_by_id(info_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Info.status).where(Info.id == info_id)
        )
        status = result.scalar_one_or_none()  # Получаем единственное значение или None
        return status  # Вернет True / False / None, если записи нет
async def update_info_status(id: int):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(Info).where(Info.id == id)
            )
            info = result.scalars().first()

            if info:
                info.status = True
                await session.commit()
                return info  # Можно вернуть обновлённую запись
            else:
                return None  # Если ничего не найдено
async def get_audio_info(video_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Info.format_id, Info.size)
            .where(Info.video_id == video_id)
            .where(Info.type == 'Audio')
        )
        audio_info = result.first()

        if audio_info:
            audio_id, audio_size = audio_info
            return audio_id, audio_size
        return None, None  # Если аудио не найдено
async def get_video_formats(video_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Info.format_id, Info.resolution, Info.size, Info.status)  # добавил Info.status
            .where(Info.video_id == video_id, Info.type == "Video")
        )

        infos = result.all()  # Получаем список кортежей

        # Преобразуем в список словарей
        format_list = [
            {"format_id": f_id, "resolution": res, "filesize": size, "status": status}
            for f_id, res, size, status in infos  # Теперь данных ровно столько, сколько надо
        ]

        # Функция для извлечения ширины (первого числа из "1920x1080")
        def extract_width(resolution):
            match = re.match(r"(\d+)", resolution)  # Берем первую цифру
            return int(match.group(1)) if match else 0

        # Сортируем список по ширине (из resolution)
        format_list.sort(key=lambda x: extract_width(x["resolution"]))

        return format_list  # Возвращаем отсортированный список
async def get_formats_by_video_id(video_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Info.format_id, Info.resolution, Info.size, Info.status, Info.type)
            .where(Info.video_id == video_id)
        )

        infos = result.all()

        # Преобразуем в список словарей
        format_list = [
            {
                "format_id": f_id,
                "resolution": res,
                "filesize": size,
                "status": status,
                "type": _type,
            }
            for f_id, res, size, status, _type in infos
        ]

        # Аудио — те, у кого type == 'Audio'
        audio_formats = [f for f in format_list if f["type"] == "Audio"]

        # Видео — всё остальное
        video_formats = [f for f in format_list if f["type"] != "Audio"]

        # Сортировка видео по ширине (1920x1080 → 1920)
        def extract_width(resolution):
            if resolution:
                match = re.match(r"(\d+)", resolution)
                return int(match.group(1)) if match else 0
            return 0

        video_formats.sort(key=lambda x: extract_width(x["resolution"]))

        # Объединяем, аудио первыми
        return audio_formats + video_formats
async def get_info_id(video_id: int, format_id: str):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(Info.id)
                .where(Info.video_id == video_id, Info.format_id == format_id)
            )
            info_id = result.scalars().first()  # Получаем id, если найдено

            return info_id
async def get_format_id_by_id(info_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Info.format_id).where(Info.id == info_id)
        )
        format_id = result.scalar_one_or_none()
        return format_id  # Вернет строку или None, если записи нет
async def get_info_by_video_and_format(video_id: int, format_id: str):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(Info).where(
                    Info.video_id == video_id,
                    Info.format_id == format_id
                )
            )
            info_obj = result.scalars().first()  # Получаем сам объект Info
            return info_obj