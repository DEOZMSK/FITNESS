"""Main menu reply keyboard."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BUTTON_ABOUT = "👩‍🏫 Обо мне"
BUTTON_DIAGNOSTICS = "🧪 Фитнес-диагностика"
BUTTON_MY_DATA = "📊 Мои данные"
BUTTON_CONTACT = "💬 Написать Лене"

BUTTON_PROFILE_START = "🚀 Начать / обновить данные"
BUTTON_BODY_CALC = "🧮 Калькуляторы тела"
BUTTON_CALORIES = "🔥 Калории и БЖУ"
BUTTON_CALIPER = "📏 Калипер / % жира / LBM"
BUTTON_FLEXIBILITY = "🧍 Гибкость"
BUTTON_CONTRAINDICATIONS = "🛡 Противопоказания"
BUTTON_FINAL_REPORT = "📊 Итоговый отчёт"


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BUTTON_ABOUT), KeyboardButton(text=BUTTON_DIAGNOSTICS)],
            [KeyboardButton(text=BUTTON_MY_DATA), KeyboardButton(text=BUTTON_CONTACT)],
        ],
        resize_keyboard=True,
    )


def get_diagnostics_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BUTTON_PROFILE_START), KeyboardButton(text=BUTTON_BODY_CALC)],
            [KeyboardButton(text=BUTTON_CALORIES), KeyboardButton(text=BUTTON_CALIPER)],
            [KeyboardButton(text=BUTTON_FLEXIBILITY), KeyboardButton(text=BUTTON_CONTRAINDICATIONS)],
            [KeyboardButton(text=BUTTON_FINAL_REPORT)],
            [KeyboardButton(text="🏠 Главное меню")],
        ],
        resize_keyboard=True,
    )
