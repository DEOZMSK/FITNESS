"""Main and diagnostics reply keyboards."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BUTTON_ABOUT = "👩‍🏫 Обо мне"
BUTTON_DIAGNOSTICS = "🧪 Фитнес-диагностика"
BUTTON_CONTACT = "💬 Написать Лене"

BUTTON_RESULT_REPORT = "📊 Итоговый отчёт"
BUTTON_RESULT_MY_DATA = "👤 Мои данные"
BUTTON_RESULT_UPDATE = "🔄 Обновить данные"

BUTTON_VIEW_RESULTS = "📊 Посмотреть прошлые результаты"
BUTTON_RETAKE = "🔄 Пройти заново"

BUTTON_SEX_WOMAN = "Женщина"
BUTTON_SEX_MAN = "Мужчина"

BUTTON_SKIP_PRESSURE = "Не знаю / пропустить"
BUTTON_SKIP_SITTING = "Пропустить"
BUTTON_YES = "Да"
BUTTON_NO = "Нет"
BUTTON_DONT_KNOW = "Не знаю"
BUTTON_KEEP = "✅ Оставить"
BUTTON_REENTER = "✏️ Ввести заново"
BUTTON_CONSULT_YES = "✍️ Задать вопрос"
BUTTON_CONSULT_NO = "⏭️ Пропустить"


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BUTTON_ABOUT), KeyboardButton(text=BUTTON_DIAGNOSTICS)],
        ],
        resize_keyboard=True,
    )


def get_post_diagnostics_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BUTTON_RESULT_REPORT), KeyboardButton(text=BUTTON_RESULT_MY_DATA)],
            [KeyboardButton(text=BUTTON_RESULT_UPDATE)],
            [KeyboardButton(text="🏠 Главное меню")],
        ],
        resize_keyboard=True,
    )


def get_existing_profile_actions_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BUTTON_VIEW_RESULTS), KeyboardButton(text=BUTTON_RETAKE)],
            [KeyboardButton(text="🏠 Главное меню")],
        ],
        resize_keyboard=True,
    )
