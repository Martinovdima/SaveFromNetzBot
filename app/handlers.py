from rest import EMOJIS, ERROR_TEXT, ERROR_IMAGE, LOAD_IMAGE, START_IMAGE, FAILS_IMAGE, YOUTUBE_REGEX, TIKTOK_REGEX,\
                                    INFO_MESSAGE, VK_VIDEO_REGEX, is_under_2gb, user_messages, delete_keyboard_message, is_playlist_url
from yout import sanitize_filename, get_video_info, filter_best_formats, convert_webm_to_m4a,\
                                                                                download_and_merge_by_format
from vk import get_vk_video_info, get_formats_vk_video, download_vk_video_async, get_format_id_from_callback
from tik import get_tiktok_video_info, download_tiktok_video, get_tiktok_video_details, create_caption
from app.keyboards import main_kb, make_keyboard_vk, main_kb_tt
from db import get_db, update_or_create_user, count_users
from aiogram import Router, Bot, types, exceptions
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from app.states import DownloadState
from aiogram.filters import Command
from datetime import datetime

from dotenv import load_dotenv
from config import logging

import emoji
import sys
import re
import os


router = Router()

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()


@router.message(DownloadState.downloading)
async def block_messages(message: types.Message):
    await message.answer("⏳ Видео загружается, подождите немного...")


@router.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer_photo(photo=START_IMAGE, caption="Просто отправьте ссылку на видео YouTube, VK или Tik Tok, и\
                                                            я предоставлю варианты для скачивания!")


@router.message(Command("admin"))
async def admin_handler(message: types.Message):
    db = next(get_db())  # Получаем сессию БД
    user_count = count_users(db)
    await message.answer(text=f'Всего пользователей в базе {user_count}')


@router.message(lambda message: re.search(YOUTUBE_REGEX, message.text, re.IGNORECASE))
async def youtube_handler(message: types.Message, state: FSMContext, bot: Bot):
    url = message.text.strip()
    user_id = message.from_user.id
    db = next(get_db())

    logging.debug(f"Получено сообщение от пользователя {user_id}: ссылка ЮТУБ {url}")
    if delete_keyboard_message(user_id):
        await bot.delete_message(chat_id=user_id, message_id=user_messages[user_id])
        del user_messages[user_id]
    if is_playlist_url(url):
        await message.answer(text='Эта ссылка содержит плейлист! Скачивание плейлиста на данный момент не возможно!')
        await bot.send_message(chat_id=user_id, text=f'\n\n Жду следующую ссылку.... \n\n')
        return

    try:
        msg_info = await message.reply_photo(photo=LOAD_IMAGE, caption=emoji.emojize(EMOJIS['wait']) + INFO_MESSAGE)

        audio_id, audio_size, title, thumbnail, info, video_id = await get_video_info(url)
        title_sanitaze = await sanitize_filename(title)

        update_or_create_user(db, user_id, url, video_id, title_sanitaze)
        logging.info(f"Данные от пользователя {user_id} сохранены в базе данных")

        if not info:
            await message.reply(text=emoji.emojize(EMOJIS['warning']) + "Не удалось найти доступные форматы для этого видео.")
            logging.info(f"Нет доступных форматов для {video_id}")
            return

        filtered_formats = await filter_best_formats(info.get("formats", []))
        msg_keyboard = await message.reply_photo(
            thumbnail,
            caption=f"Видео: {title}\n\n {emoji.emojize(EMOJIS['tv'])} Выберите формат для скачивания:",
            reply_markup=await main_kb(filtered_formats, audio_id, audio_size)
        )

        user_messages[user_id] = msg_keyboard.message_id
        logging.info(f"Клавиатура сформированна и отправлена пользователю {user_id}")
        await msg_info.delete()

    except Exception as e:
        logging.error(f"ОШИБКА процесса обработки ссылки на Youtube от пользователя {user_id}: - {e}")
        await message.reply_photo(photo=ERROR_IMAGE, caption=ERROR_TEXT)
        await bot.send_message(chat_id=user_id, text=f'\n\n Жду следующую ссылку.... \n\n')
        if 'msg_info' in locals():
            await msg_info.delete()


@router.message(lambda message: re.search(TIKTOK_REGEX, message.text, re.IGNORECASE))
async def tiktok_handler(message: types.Message, bot: Bot):
    url = message.text.strip()
    user_id = message.from_user.id

    logging.debug(f"Получено сообщение от пользователя {user_id}: ссылка ТИКТОК {url}")
    if delete_keyboard_message(user_id):
        await bot.delete_message(chat_id=user_id, message_id=user_messages[user_id])
        del user_messages[user_id]

    try:
        msg_info = await message.reply_photo(photo=LOAD_IMAGE, caption=emoji.emojize(EMOJIS['wait']) + INFO_MESSAGE)
        video_info, author, thumbnail_url, video_id = get_tiktok_video_info(url)
        format_id = get_tiktok_video_details(video_info)
        title_sanitaze = await sanitize_filename(video_info['title'])

        db = next(get_db())
        update_or_create_user(db, user_id, url, video_id, title_sanitaze)
        logging.info(f"Данные от пользователя {user_id} сохранены в базе данных")

        msg_keyboard = await message.reply_photo(
            thumbnail_url,
            caption=f"Видео: {title_sanitaze}\n\n {emoji.emojize(EMOJIS['tv'])} Выберите формат для скачивания:",
            reply_markup=await main_kb_tt(format_id)
        )

        user_messages[user_id] = msg_keyboard.message_id
        logging.info(f"Клавиатура сформирована и отправлена пользователю {user_id}")
        await msg_info.delete()
    except Exception as e:
        logging.error(f"ОШИБКА процесса обработки ссылки на TikTok от пользователя {user_id}: - {e}")
        await message.reply_photo(photo=ERROR_IMAGE, caption=ERROR_TEXT)
        await bot.send_message(chat_id=user_id, text=f'\n\n Жду следующую ссылку.... \n\n')
        if 'msg_info' in locals():
            await msg_info.delete()


@router.message(lambda message: re.search(VK_VIDEO_REGEX, message.text, re.IGNORECASE))
async def vk_video_handler(message: types.Message, state: FSMContext, bot: Bot):
    url = message.text.strip()
    user_id = message.from_user.id

    logging.debug(f"Получено сообщение от пользователя {user_id}: ссылка ВК {url}")
    if delete_keyboard_message(user_id):
        await bot.delete_message(chat_id=user_id, message_id=user_messages[user_id])
        del user_messages[user_id]

    try:
        msg_info = await message.reply_photo(photo=LOAD_IMAGE, caption=emoji.emojize(EMOJIS['wait']) + INFO_MESSAGE)
        video_vk_info, author, thumbnail_url, video_id, duration = get_vk_video_info(url)  # Распаковываем данные

        title_sanitaze = await sanitize_filename(video_vk_info['title'])
        FORMAT_DICT = get_formats_vk_video(video_vk_info)
        await state.update_data(format_dict=FORMAT_DICT)
        logging.debug(f"Сохранено в state: {FORMAT_DICT}")

        db = next(get_db())
        update_or_create_user(db, user_id, url, video_id, title_sanitaze)
        logging.info(f"Данные от пользователя {user_id} сохранены в базе данных")

        msg_keyboard = await message.reply_photo(
            thumbnail_url,
            caption=f"Видео: {title_sanitaze}\n\n {emoji.emojize(EMOJIS['tv'])} Выберите формат для скачивания:",
            reply_markup=await make_keyboard_vk(FORMAT_DICT, duration)
        )

        user_messages[user_id] = msg_keyboard.message_id
        logging.info(f"Клавиатура сформированна и отправлена пользователю {user_id}")
        await msg_info.delete()

    except Exception as e:
        logging.error(f"ОШИБКА процесса обработки ссылки на VK video от пользователя {user_id}: - {e}")
        await message.reply_photo(photo=ERROR_IMAGE, caption=ERROR_TEXT)
        await bot.send_message(chat_id=user_id, text=f'\n\n Жду следующую ссылку.... \n\n')
        if 'msg_info' in locals():
            await msg_info.delete()


@router.message()  # Этот хэндлер сработает, если ни один другой не подошёл
async def handle_invalid_message(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    if delete_keyboard_message(user_id):
        await bot.delete_message(chat_id=user_id, message_id=user_messages[user_id])
        del user_messages[user_id]
    logging.info(f"Сообщение в неправильном формате получено от пользователя {user_id} ***FAILED_LINK***")
    await message.answer_photo(photo=FAILS_IMAGE, caption="❌ Неправильный формат ссылки. Отправьте корректную ссылку на видео.")


@router.callback_query(lambda call: call.data.startswith('yt_video:') or call.data.startswith('yt_audio:'))
async def download_handler(callback_query: types.CallbackQuery, bot:Bot, state: FSMContext):
    format_id = callback_query.data.split(':')[1]
    user_id = callback_query.from_user.id
    file_size_id = callback_query.data.split(':')[2]

    # Устанавливаем состояние "downloading"
    await state.set_state(DownloadState.downloading)

    try:
        if is_under_2gb(file_size_id):
            await callback_query.answer("К сожалению телеграмм не позволяет скачивать файлы больше 2 Гб.", show_alert=True)
            await bot.send_message(chat_id=user_id, text=f'\n\n Жду следующую ссылку.... \n\n')
            return
        db = next(get_db())

        logging.info(f"Пользователь на клавиатуре {user_id} выбрал формат видео {format_id}")

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
                    logging.info(f"УСПЕХ: Сообщение с клавиатурой скрыто у пользователя {user_id}, скачивание началось")
                except Exception as e:
                    logging.warning(f"ОШИБКА: Произошла ошибка при попытке сокрытия клавиатуры у {user_id}: {e}")

            # Скачивание видео
            output_file, video_info = await download_and_merge_by_format(db, user_id, format_id)
            if output_file == None:
                await callback_query.message.reply(
                    text=emoji.emojize(EMOJIS['warning']) + "Данное видео скорее всего заблокировано в вашем регионе.",
                    disable_web_page_preview=True
                )
                await bot.send_message(chat_id=user_id, text=f'\n\n Жду следующую ссылку.... \n\n')
                return
            logging.info(f"УСПЕХ: Видео для пользователя {user_id} УСПЕШНО СКАЧАНО {output_file}")

            # Проверка и конвертация аудио
            if callback_query.data.startswith('yt_audio'):
                if output_file.endswith('.webm'):
                    output_file = await convert_webm_to_m4a(output_file)
                    logging.info(f"УСПЕХ: Аудио файл полученный от пользователя {user_id}: {output_file} переконвертировался в M4A")

            # Проверка размера файла
            file_size = os.path.getsize(output_file)
            if file_size > 2 * 1024 * 1024 * 1024:  # 2 GB
                await callback_query.message.reply(
                    text=emoji.emojize(EMOJIS['warning']) + "Файл больше 2 ГБ, отправка невозможна.",
                    disable_web_page_preview=True
                )
                logging.warning(f"ОШИБКА: {output_file} файл слишком большой ({file_size} byte) для пользователя {user_id}")
                os.remove(output_file)
                logging.info(f"Файл {output_file} УДАЛЕН! ")
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
            if callback_query.data.startswith('yt_audio'):
                audio_file = FSInputFile(output_file)
                await callback_query.message.answer_audio(
                    audio=audio_file,
                    caption=caption,
                    parse_mode=None,
                    supports_streaming=True
                )
                logging.info(f"УСПЕХ: Аудио файл отправлен пользователю {user_id}: {output_file}")
            else:
                video_file = FSInputFile(output_file)
                await callback_query.message.answer_video(
                    video=video_file,
                    caption=caption,
                    parse_mode=None,
                    supports_streaming=True
                )
                logging.info(f"УСПЕХ: Видео файл отправлен пользователю {user_id}: {output_file}")

            if os.path.exists(output_file):
                os.remove(output_file)
                logging.info(f"УСПЕХ: Файл {output_file} УДАЛЕН! ")

            # Удаление старого сообщения с клавиатурой
            if user_id in user_messages:
                try:
                    await bot.delete_message(chat_id=user_id, message_id=user_messages[user_id])
                    del user_messages[user_id]
                    logging.info(f"УСПЕХ: Старое сообщение с клавиатурой УДАЛЕНО {user_id}")
                except Exception as e:
                    logging.warning(f"ОШИБКА:  при удалении старой клавиатуры {user_id}: {e}")
            await bot.send_message(chat_id=user_id, text=f'\n\n Жду следующую ссылку.... \n\n')

        except Exception as e:
            logging.error(f"ОШИБКА: файл не удалось скачать {user_id}: {e}")

            # Удаление сообщения при ошибке
            if user_id in user_messages:
                try:
                    await bot.delete_message(chat_id=user_id, message_id=user_messages[user_id])
                    del user_messages[user_id]
                    logging.info(f"клавиатура удалена после ОШИБКИ скачивания файла {user_id}")
                except Exception as e:
                    logging.warning(f"ОШИБКА: клавиатура не удалена после ОШИКИ при скачивании файла {user_id}: {e}")
            await bot.send_message(chat_id=user_id, text=f'\n\n Жду следующую ссылку.... \n\n')

            if callback_query.message:
                try:
                    await callback_query.message.reply_photo(photo=ERROR_IMAGE, caption=ERROR_TEXT)
                except exceptions.TelegramBadRequest:
                    await bot.send_photo(chat_id=callback_query.from_user.id, photo=ERROR_IMAGE, caption=ERROR_TEXT)
            else:
                await bot.send_photo(chat_id=callback_query.from_user.id, photo=ERROR_IMAGE, caption=ERROR_TEXT)
    finally:
        # Сбрасываем состояние после завершения скачивания
        await state.clear()


@router.callback_query(lambda call: call.data.startswith('tt_download:') or call.data.startswith('tt_download_audio:'))
async def tt_download_handler(callback_query: types.CallbackQuery, bot: Bot, state:FSMContext):
    format_id = callback_query.data.split(':')[1]
    file_size_id = callback_query.data.split(':')[2]
    if is_under_2gb(file_size_id):
        await callback_query.answer("К сожалению телеграмм не позволяет скачивать файлы больше 2 Гб.", show_alert=True)
        return
    user_id = callback_query.from_user.id
    await state.set_state(DownloadState.downloading)
    try:
        db = next(get_db())

        logging.info(f"Пользователь на клавиатуре {user_id} выбрал формат видео {format_id}")

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
                    logging.info(f"УСПЕХ: Сообщение с клавиатурой скрыто у пользователя {user_id}, скачивание началось")
                except Exception as e:
                    logging.warning(f"ОШИБКА: Произошла ошибка при попытке сокрытия клавиатуры у {user_id}: {e}")

            # Скачивание видео
            output_file, video_info = await download_tiktok_video(db, user_id, format_id)
            if output_file is None or video_info is None:
                logging.error("Ошибка: download_tiktok_video() вернула None!")
                await callback_query.message.answer("⚠️ Видео недоступно или удалено. Попробуйте ещё раз.")
                return
            logging.info(f"УСПЕХ: Видео для пользователя {user_id} УСПЕШНО СКАЧАНО {output_file}")

            # Если нужно аудио, конвертируем
            if callback_query.data.startswith('tt_download_audio:'):
                if output_file.endswith('.webm'):
                    output_file = await convert_webm_to_m4a(output_file)
                    logging.info(f"УСПЕХ: Аудио файл полученный от пользователя {user_id}: {output_file} переконвертировался в M4A")

            # Проверка размера файла
            file_size = os.path.getsize(output_file)
            if file_size > 2 * 1024 * 1024 * 1024:  # 2 GB
                await callback_query.message.reply(
                    text=emoji.emojize(EMOJIS['warning']) + "К сожалению, Telegram не позволяет отправлять файлы больше 2 ГБ.",
                    disable_web_page_preview=True
                )
                logging.warning(f"ОШИБКА: {output_file} файл слишком большой ({file_size} byte) для пользователя {user_id}")
                await bot.send_message(chat_id=user_id, text=f'\n\n Жду следующую ссылку.... \n\n')
                os.remove(output_file)
                logging.info(f"Файл {output_file} УДАЛЕН! ")
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
                logging.info(f"УСПЕХ: Аудио файл отправлен пользователю {user_id}: {output_file}")
            else:
                video_file = FSInputFile(output_file)
                await callback_query.message.answer_video(
                    video=video_file,
                    caption=caption,
                    parse_mode=None,
                    supports_streaming=True
                )
                logging.info(f"УСПЕХ: Видео файл отправлен пользователю {user_id}: {output_file}")

            if os.path.exists(output_file):
                os.remove(output_file)
                logging.info(f"Файл{output_file} УДАЛЕН!")

            # Удаление старого сообщения с клавиатурой
            if user_id in user_messages:
                try:
                    await bot.delete_message(chat_id=user_id, message_id=user_messages[user_id])
                    del user_messages[user_id]
                    logging.info(f"УСПЕХ: Старое сообщение с клавиатурой УДАЛЕНО {user_id}")
                except Exception as e:
                    logging.warning(f"ОШИБКА: при удалении клавиатуры у {user_id}: {e}")
            await bot.send_message(chat_id=user_id, text=f'\n\n Жду следующую ссылку.... \n\n')

        except Exception as e:
            logging.error(f"ОШИБКА: при скачивании файла у {user_id}: {e}")

            # Удаление старого сообщения при ошибке
            if user_id in user_messages:
                try:
                    await bot.delete_message(chat_id=user_id, message_id=user_messages[user_id])
                    del user_messages[user_id]
                    logging.info(f"Старое сообщение с клавиатурой УДАЛЕНО {user_id}")
                except Exception as e:
                    logging.warning(f"ОШИБКА: при удалении клавиатуры у {user_id}: {e}")
            await bot.send_message(chat_id=user_id, text=f'\n\n Жду следующую ссылку.... \n\n')

            if callback_query.message:
                try:
                    await callback_query.message.reply_photo(photo=ERROR_IMAGE, caption=ERROR_TEXT)
                except exceptions.TelegramBadRequest:
                    await bot.send_photo(chat_id=callback_query.from_user.id, photo=ERROR_IMAGE, caption=ERROR_TEXT)
            else:
                await bot.send_photo(chat_id=callback_query.from_user.id, photo=ERROR_IMAGE, caption=ERROR_TEXT)
    finally:
        await state.clear()


@router.callback_query(lambda call: call.data.startswith('vk_video:') or call.data.startswith('vk_audio:'))
async def vk_download_handler(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    user_data = await state.get_data()
    FORMAT_DICT = user_data.get("format_dict", {})
    format_id = get_format_id_from_callback(callback_query.data, FORMAT_DICT)
    file_size_id = callback_query.data.split(':')[2]
    if is_under_2gb(file_size_id):
        await callback_query.answer("К сожалению телеграмм не позволяет скачивать файлы больше 2 Гб.", show_alert=True)
        return
    user_id = callback_query.from_user.id
    await state.set_state(DownloadState.downloading)
    try:
        db = next(get_db())

        logging.info(f"Пользователь на клавиатуре {user_id} выбрал формат видео {format_id}")
        try:
            if user_id in user_messages:
                try:
                    await bot.edit_message_caption(
                        chat_id=callback_query.message.chat.id,
                        message_id=user_messages[user_id],  # Используем ID сохраненного сообщения
                        caption=emoji.emojize(EMOJIS['download']) + ' Скачивание началось...',
                        reply_markup=None  # Убираем клавиатуру
                    )
                    logging.info(f"УСПЕХ: Сообщение с клавиатурой скрыто у пользователя {user_id}, скачивание началось")
                except Exception as e:
                    logging.warning(f"ОШИБКА: Произошла ошибка при попытке сокрытия клавиатуры у {user_id}: {e}")

            # Скачиваем и объединяем файл
            output_file, video_info = await download_vk_video_async(db, user_id, format_id)
            if output_file is None or video_info is None:
                logging.error("Ошибка: download_vk_video() вернула None!")
                await callback_query.message.answer("⚠️ Видео недоступно или удалено. Попробуйте ещё раз.")
                return
            logging.info(f"УСПЕХ: Видео для пользователя {user_id} УСПЕШНО СКАЧАНО {output_file}")

            if callback_query.data.split(':')[0] == 'vk_audio:':
                if output_file.endswith('.webm'):
                    output_path = await convert_webm_to_m4a(output_file)
                    output_file = output_path
                    logging.info(
                        f"УСПЕХ: Аудио файл полученный от пользователя {user_id}: {output_file} переконвертировался в M4A")


            # Проверка размера файла
            file_size = os.path.getsize(output_file)
            if file_size > 2 * 1024 * 1024 * 1024:  # 2 GB
                await callback_query.message.reply(text=emoji.emojize(EMOJIS['warning']) + "К сожалению, Telegram\
                                        не позволяет отправлять файлы больше 2 ГБ.", disable_web_page_preview=True)
                await bot.send_message(chat_id=user_id, text=f'\n\n Жду следующую ссылку.... \n\n')
                logging.warning(f"ОШИБКА: {output_file} файл слишком большой ({file_size} byte) для пользователя {user_id}")
                os.remove(output_file)
                logging.info(f"Файл {output_file} УДАЛЕН! ")
                return


            # Формируем описание (caption) для видео
            duration = video_info.get('duration', 0)
            # Ищем нужный формат по format_id
            selected_format = None
            best_resolution = "Неизвестно"  # Объявляем переменную заранее

            if "formats" in video_info:
                for fmt in video_info["formats"]:
                    if fmt.get("vcodec") != "none" and fmt.get("format_id") == format_id:
                        selected_format = fmt
                        break

            if selected_format:
                width = selected_format.get("width")
                height = selected_format.get("height")
                best_resolution = f"{width}x{height}" if width and height else "Неизвестно"
            # Формируем caption
            caption_v = (
                f"{emoji.emojize(EMOJIS['title'])} Название: {video_info.get('title', 'Неизвестно')}\n"
                f"{emoji.emojize(EMOJIS['autor'])} Автор: {video_info.get('uploader', 'Неизвестно')}\n"
                f'\n'
                f"{emoji.emojize(EMOJIS['durations'])} Длительность: {int(duration // 60)} минут {int(duration % 60)} сек\n"
                f'\n'
                f"{emoji.emojize(EMOJIS['resolutions'])} Разрешение: {best_resolution}\n"
                f"{emoji.emojize(EMOJIS['size'])} Размер файла: {file_size_id}\n"
            )
            caption_a = (
                f"{emoji.emojize(EMOJIS['title'])} Название: {video_info.get('title', 'Неизвестно')}\n"
                f"{emoji.emojize(EMOJIS['autor'])} Автор: {video_info.get('uploader', 'Неизвестно')}\n"
                f'\n'
                f"{emoji.emojize(EMOJIS['durations'])} Длительность: {int(duration // 60)} минут {int(duration % 60)} сек\n"
                f'\n'
                f"{emoji.emojize(EMOJIS['size'])} Размер файла: {file_size_id}\n"
            )
            # Отправляем аудио
            if callback_query.data.split(':')[0] == 'vk_audio:' or output_file.endswith('.m4a'):
                audio_file = FSInputFile(output_file)
                await callback_query.message.answer_audio(
                    audio=audio_file,
                    caption=caption_a,
                    parse_mode=None,  # Обязательно для работы ссылок
                    supports_streaming=True  # Указывает, что видео можно смотреть в потоковом режиме
                )
                logging.info(f"УСПЕХ: Аудио файл отправлен пользователю {user_id}: {output_file}")
            else:
                # Выгружаем видео в телеграмм
                video_file = FSInputFile(output_file)
                await callback_query.message.answer_video(
                    video=video_file,
                    caption=caption_v,
                    parse_mode=None,
                    supports_streaming=True
                )
                logging.info(f"УСПЕХ: Видео файл отправлен пользователю {user_id}: {output_file}")

            if os.path.exists(output_file):
                os.remove(output_file)
                logging.info(f"Файл {output_file} УДАЛЕН!")

            # После завершения скачивания удаляем старое сообщение с клавиатурой
            if user_id in user_messages:
                try:
                    await bot.delete_message(chat_id=user_id, message_id=user_messages[user_id])
                    del user_messages[user_id]  # Удаляем ID сообщения после удаления
                    logging.info(f"УСПЕХ: Старое сообщение с клавиатурой УДАЛЕНО {user_id}")
                except Exception as e:
                    logging.warning(f"Ошибка при удалении сообщения с клавиатурой {user_id} : {e}")
            await bot.send_message(chat_id=user_id, text=f'\n\n Жду следующую ссылку.... \n\n')

        except Exception as e:
            logging.warning(f"ОШИБКА: при скачивании файла: {e}")
            # После завершения скачивания удаляем старое сообщение с клавиатурой
            if user_id in user_messages:
                try:
                    await bot.delete_message(chat_id=user_id, message_id=user_messages[user_id])
                    del user_messages[user_id]  # Удаляем ID сообщения после удаления
                except Exception as e:
                    logging.warning(f"Ошибка при удалении сообщения: {e}")
            await bot.send_message(chat_id=user_id, text=f'\n\n Жду следующую ссылку.... \n\n')
            if callback_query.message:
                try:
                    await callback_query.message.reply_photo(photo=ERROR_IMAGE, caption=ERROR_TEXT)
                except exceptions.TelegramBadRequest:
                    await bot.send_photo(chat_id=callback_query.from_user.id, photo=ERROR_IMAGE, caption=ERROR_TEXT)
            else:
                await bot.send_photo(chat_id=callback_query.from_user.id, photo=ERROR_IMAGE, caption=ERROR_TEXT)
    finally:
        await state.clear()





