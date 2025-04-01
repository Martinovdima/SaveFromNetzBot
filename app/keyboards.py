from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from rest import EMOJIS
import emoji

find_yt_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔍 Поиск на YouTube", switch_inline_query_current_chat="")]
])


def all_videos_channel(id_channel):
    return InlineKeyboardMarkup(inline_keyboard=[
        #[InlineKeyboardButton(text="✅ Подписаться", callback_data="subcribe")],
        [InlineKeyboardButton(text="🔍 Все видео с канала", switch_inline_query_current_chat=f"channel_id_{id_channel}")]
    ])


async def main_kb(filtered_formats, audio_id, audio_size, video) -> InlineKeyboardMarkup:
    button_list = []
    audio_full_size = f'{round(audio_size / (1024 ** 2), 2)} MB'
    button_list.append([InlineKeyboardButton(
        text=f" Cкачать {emoji.emojize(EMOJIS['sound'])} аудио {emoji.emojize(EMOJIS['size'])} {audio_full_size}",
        callback_data=f"yt_audio:{audio_id}:{audio_full_size}:{video}")])

    for f in filtered_formats:
        format_id = f['format_id']
        if format_id:
            callback_data = f"yt_video:{f['format_id']}:{f['filesize']}:{video}"
            button_list.append([InlineKeyboardButton(
                text=f" Cкачать {emoji.emojize(EMOJIS['resolutions'])} {f['resolution']:<10} {emoji.emojize(EMOJIS['size'])}  {f['filesize']:<10}",
                callback_data=callback_data)])

    # Создаем клавиатуру с кнопками
    keyboard = InlineKeyboardMarkup(inline_keyboard=button_list)
    return keyboard


async def make_keyboard_vk(formats_dict, duration):
    """
        Создаёт клавиатуру с кнопками для скачивания аудио и видео из VK.

        Args:
            formats_dict (dict[int, list]): Словарь форматов, где ключ — номер формата,
                                            значение — список с одним словарем (формат видео/аудио).
            duration (int | None): Длительность видео в секундах или None, если неизвестно.

        Returns:
            InlineKeyboardMarkup: Объект клавиатуры с кнопками загрузки.
        """
    button_list = []

    for num, format_list in formats_dict.items():
        f = format_list[0]  # Достаём единственный элемент списка

        resolution_text = "Аудио" if f.get(
            "width") is None else f"{f.get('width', 'Неизвестно')}x{f.get('height', 'Неизвестно')}"

        # Проверяем, есть ли 'tbr' и 'duration'
        if 'tbr' in f and isinstance(f['tbr'], (int, float)) and duration:
            # Рассчитываем размер файла
            file_size = (f['tbr'] * duration) / (8 * 1024)  # в МБ
            size_text = f"{round(file_size, 2)} MB"
        else:
            # Если данных недостаточно, выводим "Неизвестно"
            size_text = "Неизвестно"

        # Определяем тип callback
        callback_type = "vk_audio" if resolution_text == "Аудио" else "vk_video"

        button_list.append([
            InlineKeyboardButton(
                text=f"Скачать {emoji.emojize(EMOJIS['sound'] if resolution_text == 'Аудио' else EMOJIS['resolutions'])} {resolution_text} {emoji.emojize(EMOJIS['size'])} {size_text}",
                callback_data=f"{callback_type}:{num}:{size_text}"  # Используем номер формата
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=button_list)


async def main_kb_tt(formats):
    button_list = []

    for f in formats:
        button_list.append([InlineKeyboardButton(
            text=f" Cкачать {emoji.emojize(EMOJIS['resolutions'])} {f['resolution']} {emoji.emojize(EMOJIS['size'])}  {f['size']}",
            callback_data=f"tt_download:{f['id']}:{f['size']}")])

    # Создаем клавиатуру с кнопками
    keyboard = InlineKeyboardMarkup(inline_keyboard=button_list)
    return keyboard
