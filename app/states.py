from aiogram.fsm.state import State, StatesGroup


class VideoProcessing(StatesGroup):
    waiting_for_processing = State()


class DownloadState(StatesGroup):
    downloading = State()

