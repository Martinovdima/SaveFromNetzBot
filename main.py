import sys
import os
import asyncio
from datetime import datetime
import re
from dotenv import load_dotenv
import logging

import emoji

from aiogram import Bot, Dispatcher, types
from aiogram.types import FSInputFile
from aiogram.filters import Command

from db import get_db, update_or_create_user, create_user_request
from yout import sanitize_filename, download_and_merge_by_format, get_video_info, filter_formats_by_vcodec_and_size, main_kb, convert_webm_to_m4a
from rest import EMOJIS, ERROR_TEXT, ERROR_IMAGE, LOAD_IMAGE, START_IMAGE, FAILS_IMAGE
from rest import YOUTUBE_REGEX, TIKTOK_REGEX, INSTAGRAM_REGEX, INFO_MESSAGE
from tik import get_tiktok_video_info, download_tiktok_video, get_tiktok_video_details, main_kb_tt, create_caption
from insta import get_insta_video_info, get_format_inst_video, main_kb_inst, download_inst_video


sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()


# Настройка логирования в файл
logging.basicConfig(
    level=logging.DEBUG,
    filename="py_log.log",
    filemode="a",  # "a" - добавлять в файл, "w" - перезаписывать
    format="%(asctime)s - %(levelname)s - %(message)s"
)

DOWNLOAD_DIR = "videos"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

bot = Bot(os.getenv('TOKEN'))
dp = Dispatcher()


# Хранение идентификаторов сообщений с клавиатурой для каждого пользователя
user_messages = {}

@dp.message(Command(commands=['start']))
async def start_handler(message: types.Message):
    await message.answer_photo(photo=START_IMAGE, caption="Просто отправьте ссылку на видео YouTube или Tik Tok, и я предоставлю варианты для скачивания!")

@dp.message(lambda message: re.search(YOUTUBE_REGEX, message.text, re.IGNORECASE))
async def youtube_handler(message: types.Message):
    url = message.text.strip()
    user_id = message.from_user.id

    logging.debug(f"Message received from user {user_id}: {url}")

    try:
        msg_info = await message.reply_photo(photo=LOAD_IMAGE, caption=emoji.emojize(EMOJIS['wait']) + INFO_MESSAGE)

        # Получаем данные о видео
        audio_id, audio_size, title, thumbnail, info, video_id = get_video_info(url)
        title_sanitaze = sanitize_filename(title)
        # Логируем полученные данные
        logging.info(f"Video ID: {video_id},Title: {title_sanitaze}")

        # Сохраняем URL в базе данных
        db = next(get_db())
        update_or_create_user(db, user_id, url, video_id, title_sanitaze)
        logging.info(f"Data saved to the database for user {user_id}")

        if not info:
            await message.reply(text=emoji.emojize(EMOJIS['warning']) + "Не удалось найти доступные форматы для этого видео.")
            return
        formats = info.get("formats", [])

        # Фильтруем форматы
        filtered_formats = filter_formats_by_vcodec_and_size(audio_size, formats, "avc1")

        # Отправляем информацию о видео и клавиатуру
        msg_keyboard = await message.reply_photo(
            thumbnail,
            caption=f"Видео: {title}\n\n {emoji.emojize(EMOJIS['tv'])} Выберите формат для скачивания:",
            reply_markup=main_kb(filtered_formats, audio_id, audio_size)
        )

        # Сохраняем ID сообщения для пользователя
        user_messages[user_id] = msg_keyboard.message_id
        logging.debug(f"Message with keyboard sent to user {user_id}")
        # Удаляем сообщения о получении информации
        await msg_info.delete()


    except Exception as e:

        logging.error(f"Error processing YouTube link from {user_id}: {e}")

        await message.reply_photo(photo=ERROR_IMAGE, caption=ERROR_TEXT)

        # Удаляем сообщение о получении информации (если успело отправиться)

        if 'msg_info' in locals():
            await msg_info.delete()

@dp.message(lambda message: re.search(TIKTOK_REGEX, message.text, re.IGNORECASE))
async def tiktok_handler(message: types.Message):
    url = message.text.strip()
    user_id = message.from_user.id

    logging.debug(f"Message received from user {user_id}: {url}")

    try:
        # Отправляем сообщение о получении информации
        msg_info = await message.reply_photo(photo=LOAD_IMAGE, caption=emoji.emojize(EMOJIS['wait']) + INFO_MESSAGE)

        # Получаем данные о видео
        video_info, author, thumbnail_url, video_id = get_tiktok_video_info(url)
        format_video = get_tiktok_video_details(video_info)
        title_sanitaze = sanitize_filename(video_info['title'])

        # Логируем полученные данные
        logging.info(f"Video ID: {video_id}, Autor: {author}, Title: {title_sanitaze}")

        # Сохраняем URL в базе данных
        db = next(get_db())
        update_or_create_user(db, user_id, url, video_id, title_sanitaze)
        logging.info(f"Data saved to the database for user {user_id}")

        # Отправляем пользователю информацию и клавиатуру
        msg_keyboard = await message.reply_photo(
            thumbnail_url,
            caption=f"Видео: {title_sanitaze}\n\n {emoji.emojize(EMOJIS['tv'])} Выберите формат для скачивания:",
            reply_markup=main_kb_tt(format_video)
        )

        # Сохраняем ID сообщения для пользователя
        user_messages[user_id] = msg_keyboard.message_id
        logging.debug(f"Message with keyboard sent to user {user_id}")

        # Удаляем сообщение о получении информации
        await msg_info.delete()

    except Exception as e:
        logging.error(f"Error processing TikTok link from {user_id}: {e}")
        await message.reply_photo(photo=ERROR_IMAGE, caption=ERROR_TEXT)

        # Удаляем сообщение о получении информации (если успело отправиться)
        if 'msg_info' in locals():
            await msg_info.delete()

# @dp.message(lambda message: re.search(INSTAGRAM_REGEX, message.text, re.IGNORECASE))
# async def instagram_handler(message: types.Message):
#     # Извлекаем данные из сообщения
#     url = message.text.strip()
#     user_id = message.from_user.id
#
#     try:
#         # Отправляем сообщение о получении информации
#         msg_info = await message.reply_photo(photo=LOAD_IMAGE, caption=emoji.emojize(EMOJIS['wait']) + INFO_MESSAGE)
#         video_inst_info, video_id, author, thumbnail_url = get_insta_video_info(url)  # Распаковываем данные
#
#         # Убираем все конфликты в названии файла
#         title_sanitaze = sanitize_filename(video_inst_info['title'])
#
#         format_inst_video = get_format_inst_video(video_inst_info)
#
#         # Сохраняем URL в базе данных
#         db = next(get_db())
#         update_or_create_user(db, user_id, url, video_id, title_sanitaze)
#
#         # Отправляем информацию о видео и клавиатуру
#         msg_keyboard = await message.reply_photo(
#             thumbnail_url,
#             caption=f"Видео: {title_sanitaze}\n\n {emoji.emojize(EMOJIS['tv'])} Выберите формат для скачивания:",
#             reply_markup=main_kb_inst(format_inst_video)
#         )
#         # Сохраняем ID сообщения для пользователя
#         user_messages[user_id] = msg_keyboard.message_id
#         # Удаляем сообщения о получении информации
#         await msg_info.delete()
#
#     except Exception as e:
#         print(f"Произошла ошибка: {e}")
#         await message.reply_photo(photo=ERROR_IMAGE, caption=ERROR_TEXT)
#         # Удаляем сообщения о получении информации
#         await msg_info.delete()
#
#         # Проверяем форматы
#         # for f in info.get('formats', []):  # Добавил .get(), чтобы избежать ошибки, если 'formats' нет
#         #     print(f"{f['format_id']} - {f['ext']} - {f.get('width', 'Неизвестно')}x{f.get('height', 'Неизвестно')} - "
#         #         f"{f.get('resolution', 'Неизвестно')} - {f.get('filesize', 'Неизвестно')} - {f.get('filesize_approx', 'Неизвестно')}")
#
#         # await message.answer_photo(photo=FAILS_IMAGE,
#         #                            caption="Мы работает над этой опцией...")

@dp.message()  # Этот хэндлер сработает, если ни один другой не подошёл
async def handle_invalid_message(message: types.Message):
    user_id = message.from_user.id
    logging.debug(f"Message received from user {user_id} ***FAILED_LINK***")
    await message.answer_photo(photo=FAILS_IMAGE, caption="❌ Неправильный формат ссылки. Отправьте корректную ссылку на видео.")

@dp.callback_query(lambda call: call.data.startswith('tt_download:') or call.data.startswith('tt_download_audio:'))
async def tt_download_handler(callback_query: types.CallbackQuery):
    format_id = callback_query.data.split(':')[1]
    user_id = callback_query.from_user.id
    db = next(get_db())

    logging.debug(f"Download request from {user_id}: format {format_id}")

    try:
        # Попытка обновить сообщение с клавиатурой
        if user_id in user_messages:
            try:
                await bot.edit_message_caption(
                    chat_id=callback_query.message.chat.id,
                    message_id=user_messages[user_id],
                    caption=emoji.emojize(EMOJIS['download']) + ' Скачивание началось...',
                    reply_markup=None
                )
                logging.info(f"Message updated for {user_id}")
            except Exception as e:
                logging.warning(f"Error updating message for {user_id}: {e}")

        # Скачивание видео
        output_file, video_info = download_tiktok_video(db, user_id, format_id)
        logging.info(f"Video downloaded for {user_id}: {output_file}")

        # Если нужно аудио, конвертируем
        if callback_query.data.startswith('tt_download_audio:'):
            if output_file.endswith('.webm'):
                output_file = convert_webm_to_m4a(output_file)
                logging.info(f"File converted to M4A for {user_id}: {output_file}")

        # Проверка размера файла
        file_size = os.path.getsize(output_file)
        if file_size > 2 * 1024 * 1024 * 1024:  # 2 GB
            await callback_query.message.reply(
                text=emoji.emojize(EMOJIS['warning']) + "К сожалению, Telegram не позволяет отправлять файлы больше 2 ГБ.",
                disable_web_page_preview=True
            )
            logging.warning(f"Fail too large ({file_size} byte) for {user_id}")
            return

        # Формируем описание для файла
        caption = create_caption(video_info, format_id)

        # Отправка файла пользователю
        if callback_query.data.startswith('tt_download_audio:'):
            audio_file = FSInputFile(output_file)
            await callback_query.message.answer_audio(
                audio=audio_file,
                caption=caption,
                parse_mode=None,
                supports_streaming=True
            )
            logging.info(f"Audio sent to user {user_id}: {output_file}")
        else:
            video_file = FSInputFile(output_file)
            await callback_query.message.answer_video(
                video=video_file,
                caption=caption,
                parse_mode=None,
                supports_streaming=True
            )
            logging.info(f"Video sent to user {user_id}: {output_file}")

        # Удаление старого сообщения с клавиатурой
        if user_id in user_messages:
            try:
                await bot.delete_message(chat_id=user_id, message_id=user_messages[user_id])
                del user_messages[user_id]
                logging.info(f"Old message with keyboard deleted for {user_id}")
            except Exception as e:
                logging.warning(f"Error deleting message for {user_id}: {e}")

    except Exception as e:
        logging.error(f"Error downloading for {user_id}: {e}")

        # Удаление старого сообщения при ошибке
        if user_id in user_messages:
            try:
                await bot.delete_message(chat_id=user_id, message_id=user_messages[user_id])
                del user_messages[user_id]
                logging.info(f"Message deleted after error for {user_id}")
            except Exception as e:
                logging.warning(f"Error deleting message after failure for {user_id}: {e}")

        await callback_query.message.reply_photo(photo=ERROR_IMAGE, caption=ERROR_TEXT)

@dp.callback_query(lambda call: call.data.startswith('download:') or call.data.startswith('download_audio:'))
async def download_handler(callback_query: types.CallbackQuery):
    format_id = callback_query.data.split(':')[1]
    user_id = callback_query.from_user.id
    db = next(get_db())

    logging.debug(f"Download request from {user_id}: format {format_id}")

    try:
        # Изменение сообщения с клавиатурой
        if user_id in user_messages:
            try:
                await bot.edit_message_caption(
                    chat_id=callback_query.message.chat.id,
                    message_id=user_messages[user_id],
                    caption=emoji.emojize(EMOJIS['download']) + ' Скачивание началось...',
                    reply_markup=None
                )
                logging.info(f"Message updated for {user_id}")
            except Exception as e:
                logging.warning(f"Error updating message for {user_id}: {e}")

        # Скачивание видео
        output_file, video_info = download_and_merge_by_format(db, user_id, format_id)
        logging.info(f"Video downloaded for {user_id}: {output_file}")

        # Проверка и конвертация аудио
        if callback_query.data.startswith('download_audio'):
            if output_file.endswith('.webm'):
                output_file = convert_webm_to_m4a(output_file)
                logging.info(f"File converted to M4A for {user_id}: {output_file}")

        # Проверка размера файла
        file_size = os.path.getsize(output_file)
        if file_size > 2 * 1024 * 1024 * 1024:  # 2 GB
            await callback_query.message.reply(
                text=emoji.emojize(EMOJIS['warning']) + "Файл больше 2 ГБ, отправка невозможна.",
                disable_web_page_preview=True
            )
            logging.warning(f"Fail {output_file} too large ({file_size} byte) for {user_id}")
            return

        # Обработка даты
        raw_date = video_info.get('upload_date', 'Нет данных')
        formatted_date = "Нет данных"
        if raw_date != 'Нет данных':
            try:
                formatted_date = datetime.strptime(raw_date, "%Y%m%d").strftime("%Y.%m.%d")
            except ValueError:
                formatted_date = "Неверный формат даты"

        # Формирование описания
        caption = (
            f"{emoji.emojize(EMOJIS['title'])} Название: {video_info['title']}\n"
            f"{emoji.emojize(EMOJIS['autor'])} Автор: {video_info['uploader']}\n\n"
            f"{emoji.emojize(EMOJIS['view'])} Просмотры: {video_info['view_count']}\n"
            f"{emoji.emojize(EMOJIS['durations'])} Длительность: {video_info['duration'] // 60} мин {video_info['duration'] % 60} сек\n"
            f"{emoji.emojize(EMOJIS['date'])} Дата загрузки: {formatted_date}\n\n"
            f"{emoji.emojize(EMOJIS['resolutions'])} Разрешение: {video_info['resolution']}\n"
            f"{emoji.emojize(EMOJIS['size'])} Размер файла: {round(file_size / (1024 ** 2), 2)} MB\n"
        )

        # Отправка пользователю
        if callback_query.data.startswith('download_audio'):
            audio_file = FSInputFile(output_file)
            await callback_query.message.answer_audio(
                audio=audio_file,
                caption=caption,
                parse_mode=None,
                supports_streaming=True
            )
            logging.info(f"Audio sent to user {user_id}: {output_file}")
        else:
            video_file = FSInputFile(output_file)
            await callback_query.message.answer_video(
                video=video_file,
                caption=caption,
                parse_mode=None,
                supports_streaming=True
            )
            logging.info(f"Video sent to user {user_id}: {output_file}")

        # Удаление старого сообщения с клавиатурой
        if user_id in user_messages:
            try:
                await bot.delete_message(chat_id=user_id, message_id=user_messages[user_id])
                del user_messages[user_id]
                logging.info(f"Old message with keyboard deleted for {user_id}")
            except Exception as e:
                logging.warning(f"Error deleting message for {user_id}: {e}")

    except Exception as e:
        logging.error(f"Error downloading for {user_id}: {e}")

        # Удаление сообщения при ошибке
        if user_id in user_messages:
            try:
                await bot.delete_message(chat_id=user_id, message_id=user_messages[user_id])
                del user_messages[user_id]
                logging.info(f"Message deleted after error for {user_id}")
            except Exception as e:
                logging.warning(f"Error deleting message after failure for {user_id}: {e}")

        await callback_query.message.reply_photo(photo=ERROR_IMAGE, caption=ERROR_TEXT)

# @dp.callback_query(lambda call: call.data.startswith('inst_download:') or call.data.startswith('inst_download_audio:'))
# async def inst_download_handler(callback_query: types.CallbackQuery):
#     format_id = callback_query.data.split(':')[1]
#     user_id = callback_query.from_user.id
#     db = next(get_db())
#     try:
#         if user_id in user_messages:
#             try:
#                 await bot.edit_message_caption(
#                     chat_id=callback_query.message.chat.id,
#                     message_id=user_messages[user_id],  # Используем ID сохраненного сообщения
#                     caption=emoji.emojize(EMOJIS['download']) + ' Скачивание началось...',
#                     reply_markup=None  # Убираем клавиатуру
#                 )
#             except Exception as e:
#                 print(f"Ошибка при изменении сообщения: {e}")
#
#         # Скачиваем и объединяем файл
#         output_file, video_info = download_inst_video(db, user_id, format_id)
#
#         if callback_query.data.split(':')[0] == 'tt_download_audio:':
#             if output_file.endswith('.webm'):
#                 output_path = convert_webm_to_m4a(output_file)
#                 output_file = output_path
#
#
#         # Проверка размера файла
#         file_size = os.path.getsize(output_file)
#         if file_size > 2 * 1024 * 1024 * 1024:  # 2 GB
#             await callback_query.message.reply(text=emoji.emojize(EMOJIS['warning']) + "К сожалению, Telegram не позволяет отправлять файлы больше 2 ГБ.", disable_web_page_preview=True)
#             return
#
#
#         # Формируем описание (caption) для видео
#         caption = create_caption(video_info, format_id)
#         # Отправляем аудио
#         if callback_query.data.split(':')[0] == 'tt_download_audio:':
#             audio_file = FSInputFile(output_file)
#             await callback_query.message.answer_audio(
#                 audio=audio_file,
#                 caption=caption,
#                 parse_mode=None,  # Обязательно для работы ссылок
#                 supports_streaming=True  # Указывает, что видео можно смотреть в потоковом режиме
#             )
#         else:
#             # Выгружаем видео в телеграмм
#             video_file = FSInputFile(output_file)
#             await callback_query.message.answer_video(
#                 video=video_file,
#                 caption=caption,
#                 parse_mode=None,
#                 supports_streaming=True
#             )
#         # После завершения скачивания удаляем старое сообщение с клавиатурой
#         if user_id in user_messages:
#             try:
#                 await bot.delete_message(chat_id=user_id, message_id=user_messages[user_id])
#                 del user_messages[user_id]  # Удаляем ID сообщения после удаления
#             except Exception as e:
#                 print(f"Ошибка при удалении сообщения: {e}")
#
#     except Exception as e:
#         # После завершения скачивания удаляем старое сообщение с клавиатурой
#         if user_id in user_messages:
#             try:
#                 await bot.delete_message(chat_id=user_id, message_id=user_messages[user_id])
#                 del user_messages[user_id]  # Удаляем ID сообщения после удаления
#             except Exception as e:
#                 print(f"Ошибка при удалении сообщения: {e}")
#         await callback_query.message.reply_photo(photo=ERROR_IMAGE, caption=ERROR_TEXT)



if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(dp.start_polling(bot, skip_updates=True))
    loop.run_forever()