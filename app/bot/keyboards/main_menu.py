"""Main menu reply keyboard."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BUTTON_ABOUT = "👩‍🏫 Обо мне"
BUTTON_DIAGNOSTICS = "🧪 Фитнес-диагностика"
BUTTON_RESULTS = "📊 Мои результаты"
BUTTON_CONTACT = "💬 Связаться с тренером"


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BUTTON_ABOUT), KeyboardButton(text=BUTTON_DIAGNOSTICS)],
        ],
        resize_keyboard=True,
    )
