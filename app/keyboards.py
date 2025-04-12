from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from rest import EMOJIS
import emoji
from data.infos_func import get_status_by_id, get_info_id
from aiogram import Bot
from aiogram.types import BotCommand


find_yt_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔍 Поиск на YouTube", switch_inline_query_current_chat="")]
])

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🔁 Перезапустить"),
            KeyboardButton(text="🔍 Поиск"),
        ],
        [
            KeyboardButton(text="👤 Профиль"),
            KeyboardButton(text="ℹ️ Справка")
        ]
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
    input_field_placeholder="Выберите действие..."
)

async def set_main_menu(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Запустить бота"),
        BotCommand(command="/search", description="Поиск по каналу"),
    ]
    await bot.set_my_commands(commands)

def all_videos_channel(id_channel):
    return InlineKeyboardMarkup(inline_keyboard=[
        #[InlineKeyboardButton(text="✅ Подписаться", callback_data="subcribe")],
        [InlineKeyboardButton(text="🔍 Все видео с канала", switch_inline_query_current_chat=f"channel_id_{id_channel}")]
    ])


async def main_kb(filtered_formats, audio_id, audio_size, video) -> InlineKeyboardMarkup:
    button_list = []
    info_id = await get_info_id(video_id=video, format_id=audio_id)
    status = await get_status_by_id(info_id)
    fire_emoji = emoji.emojize(EMOJIS['fire']) if status else ""
    audio_full_size = f'{round(audio_size / (1024 ** 2), 2)} MB'
    button_list.append([InlineKeyboardButton(
        text=(f" Cкачать {emoji.emojize(EMOJIS['sound'])} аудио {emoji.emojize(EMOJIS['size'])} {audio_full_size}"
              f'{fire_emoji}'),
        callback_data=f"yt_audio:{audio_id}:{audio_full_size}:{video}")])

    for f in filtered_formats:
        format_id = f['format_id']
        if format_id:
            fire_emoji = emoji.emojize(EMOJIS['fire']) if f.get('status') else ""
            callback_data = f"yt_video:{f['format_id']}:{f['filesize']}:{video}"
            button_list.append([InlineKeyboardButton(
                text=(
                    f" Cкачать {emoji.emojize(EMOJIS['resolutions'])} {f['resolution']} "
                    f"{emoji.emojize(EMOJIS['size'])} {f['filesize']} "
                    f"{fire_emoji}"
                ),
                callback_data=callback_data)])

    # Создаем клавиатуру с кнопками
    keyboard = InlineKeyboardMarkup(inline_keyboard=button_list)
    return keyboard


async def make_keyboard_vk(formats, video_id):
    """
    Создаёт клавиатуру с кнопками для скачивания аудио и видео из VK.

    Args:
        formats (list[dict]): Список форматов (каждый — словарь с format_id, resolution, filesize).
        video_id (int): ID видео (используется в callback).

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками загрузки.
    """
    button_list = []

    for f in formats:
        print(f)
        # Пропускаем, если размер не указан или нулевой
        if f['filesize'] in (0, '0', '0.0 MB'):
            continue

        fire_emoji = emoji.emojize(EMOJIS['fire']) if f.get('status') else ""
        res_icon = emoji.emojize(EMOJIS['sound'] if f['resolution'] == "Аудио" else EMOJIS['resolutions'])

        button_text = (
            f"Скачать {res_icon} {f['resolution']} "
            f"{emoji.emojize(EMOJIS['size'])} {f['filesize']} {fire_emoji}"
        )

        callback_type = "vk_audio" if f['resolution'] == "Аудио" else "vk_video"

        button_list.append([
            InlineKeyboardButton(
                text=button_text.strip(),
                callback_data=f"{callback_type}:{await get_info_id(video_id=video_id, format_id=f['format_id'])}:{f['filesize']}:{video_id}"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=button_list)


async def main_kb_tt(formats, video):
    button_list = []
    for f in formats:
        if f['filesize'] == 0:
            continue
        fire_emoji = emoji.emojize(EMOJIS['fire']) if f.get('status') else ""
        button_list.append([InlineKeyboardButton(
            text=(f" Cкачать {emoji.emojize(EMOJIS['resolutions'])} {f['resolution']} "
                  f"{emoji.emojize(EMOJIS['size'])} {f['filesize']}"
                  f"{fire_emoji}"),
                callback_data=f"tt_download:{f['format_id']}:{f['filesize']}:{video}")])

    # Создаем клавиатуру с кнопками
    keyboard = InlineKeyboardMarkup(inline_keyboard=button_list)
    return keyboard
