"""Handlers for showing current saved profile (Мои данные)."""

from aiogram import F, Router
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from app.bot.keyboards import (
    BUTTON_BODY_CALC,
    BUTTON_CALORIES,
    BUTTON_CONTACT,
    BUTTON_FINAL_REPORT,
    BUTTON_HOME_MENU,
    BUTTON_MY_DATA,
    BUTTON_PROFILE_START,
    get_main_menu_keyboard,
)
from app.db import Database

router = Router(name=__name__)


def _profile_actions_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✏️ Обновить данные"), KeyboardButton(text=BUTTON_BODY_CALC)],
            [KeyboardButton(text=BUTTON_CALORIES), KeyboardButton(text=BUTTON_FINAL_REPORT)],
            [KeyboardButton(text=BUTTON_CONTACT), KeyboardButton(text=BUTTON_HOME_MENU)],
        ],
        resize_keyboard=True,
    )


@router.message(F.text == BUTTON_MY_DATA)
async def show_my_data(message: Message) -> None:
    db = Database()
    profile = db.get_diagnostic_profile_by_telegram_id(message.from_user.id)
    if not profile:
        await message.answer(
            "Вы ещё не заполнили данные. Нажмите «🚀 Начать / обновить данные», чтобы бот смог сделать расчёты.",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=BUTTON_PROFILE_START)], [KeyboardButton(text=BUTTON_HOME_MENU)]],
                resize_keyboard=True,
            ),
        )
        return

    text = (
        "👤 Ваши данные:\n"
        f"Имя: {profile.get('full_name') or '—'}\n"
        f"Пол: {profile.get('sex') or '—'}\n"
        f"Возраст: {profile.get('age') or '—'}\n"
        f"Рост: {profile.get('height_cm') or '—'}\n"
        f"Вес: {profile.get('weight_kg') or '—'}\n"
        f"Талия: {profile.get('waist_cm') or '—'}\n"
        f"Бёдра: {profile.get('hips_cm') or '—'}\n"
        f"Грудь: {profile.get('chest_cm') or '—'}\n"
        f"Запястье: {profile.get('wrist_cm') or '—'}\n"
        f"Рост сидя: {profile.get('sitting_height_cm') or '—'}\n"
        f"Цель: {profile.get('goal') or '—'}\n"
        f"Ограничения: {profile.get('health_notes') or '—'}"
    )
    await message.answer(text, reply_markup=_profile_actions_keyboard())


@router.message(F.text == "✏️ Обновить данные")
async def refresh_profile(message: Message) -> None:
    await message.answer("Нажмите «🚀 Начать / обновить данные» в разделе диагностики.", reply_markup=get_main_menu_keyboard())
