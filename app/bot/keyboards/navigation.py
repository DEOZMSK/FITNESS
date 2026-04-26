"""Reusable navigation keyboards for bot scenarios."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BUTTON_BACK = "⬅️ Назад"
BUTTON_HOME_MENU = "🏠 Главное меню"
BUTTON_CANCEL = "❌ Отмена"
BUTTON_SKIP = "Пропустить"


def get_scenario_skip_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BUTTON_SKIP)],
            [KeyboardButton(text=BUTTON_CANCEL), KeyboardButton(text=BUTTON_HOME_MENU)],
        ],
        resize_keyboard=True,
    )
