import os
import asyncio
import logging
from aiogram import Bot, Dispatcher
from app.handlers import router
from config import session
from aiogram.fsm.storage.memory import MemoryStorage
from database import init_db


# Логирование (чтобы видеть ошибки)
logging.basicConfig(level=logging.INFO)

# Директория для загрузок
DOWNLOAD_DIR = "videos"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Создаём бота и диспетчер
# bot = Bot(token=os.getenv("TOKEN"), session=session, timeout=300)
bot = Bot(token=os.getenv("TOKEN"), timeout=300)
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)


async def main():
    print("Проверка: скрипт запустился!")
    try:
        await init_db()
        await dp.start_polling(bot, skip_updates=True, polling_timeout=120)
    except Exception as e:
        logging.error(f"Ошибка в боте: {e}")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')