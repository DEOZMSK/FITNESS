"""Handlers for quick diagnostics and full questionnaire."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot.states import FullQuestionnaireStates, QuickDiagnosticsStates
from app.bot.keyboards import (
    BUTTON_BACK,
    BUTTON_SKIP,
    get_main_menu_keyboard,
    get_scenario_nav_keyboard,
    get_scenario_skip_keyboard,
)
from app.data.contraindications import SAFE_STOP_MESSAGE, STOP_FACTORS
from app.db import Database
from app.services import send_diagnostics_summary

router = Router(name=__name__)


def _diag_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Быстрая диагностика", callback_data="diag:quick")],
            [InlineKeyboardButton(text="📋 Полная анкета", callback_data="diag:full")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="start:menu")],
        ]
    )


def _to_number(raw_value: str) -> float | None:
    value = raw_value.replace(",", ".").strip()
    try:
        parsed = float(value)
    except ValueError:
        return None
    if parsed <= 0:
        return None
    return parsed


def _find_stop_factors(text: str) -> list[str]:
    lowered = text.casefold()
    return [factor for factor in STOP_FACTORS if factor in lowered]


async def _get_or_create_user_id(message: Message) -> int:
    if not message.from_user:
        raise RuntimeError("Message does not contain user")
    db = Database()
    return db.upsert_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )


async def show_diagnostics_menu_message(message: Message) -> None:
    """Open diagnostics menu from reply keyboard command."""
    await message.answer(
        "🧪 Фитнес-диагностика\n\nВыберите формат прохождения:",
        reply_markup=_diag_menu_keyboard(),
    )


@router.callback_query(F.data == "diag:start")
async def show_diagnostics_menu(callback: CallbackQuery) -> None:
    """Open diagnostics menu."""
    if not callback.message:
        await callback.answer()
        return

    await callback.message.edit_text(
        "🧪 Фитнес-диагностика\n\nВыберите формат прохождения:",
        reply_markup=_diag_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "diag:quick")
async def start_quick_diagnostics(callback: CallbackQuery, state: FSMContext) -> None:
    """Start quick diagnostics flow."""
    if not callback.message:
        await callback.answer()
        return

    await state.clear()
    await state.update_data(flow="quick")
    await state.set_state(QuickDiagnosticsStates.waiting_for_name)
    await callback.message.answer(
        "Быстрая диагностика. Шаг 1/12: Как вас зовут?",
        reply_markup=get_scenario_nav_keyboard(),
    )
    await callback.answer()


@router.message(StateFilter(QuickDiagnosticsStates), F.text == BUTTON_BACK)
async def quick_back_to_start(message: Message, state: FSMContext) -> None:
    """Safe back action for quick flow (fallback to first step)."""
    await state.clear()
    await state.update_data(flow="quick")
    await state.set_state(QuickDiagnosticsStates.waiting_for_name)
    await message.answer(
        "Возвращаю к началу быстрой диагностики. Шаг 1/12: Как вас зовут?",
        reply_markup=get_scenario_nav_keyboard(),
    )


@router.message(QuickDiagnosticsStates.waiting_for_name)
async def quick_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=(message.text or "").strip())
    await state.set_state(QuickDiagnosticsStates.waiting_for_age)
    await message.answer("Шаг 2/12: Укажите возраст (полных лет).")


@router.message(QuickDiagnosticsStates.waiting_for_age)
async def quick_age(message: Message, state: FSMContext) -> None:
    value = _to_number(message.text or "")
    if value is None:
        await message.answer("Введите возраст числом, например: 29")
        return
    await state.update_data(age=int(value))
    await state.set_state(QuickDiagnosticsStates.waiting_for_gender)
    await message.answer("Шаг 3/12: Ваш пол?")


@router.message(QuickDiagnosticsStates.waiting_for_gender)
async def quick_gender(message: Message, state: FSMContext) -> None:
    await state.update_data(gender=(message.text or "").strip())
    await state.set_state(QuickDiagnosticsStates.waiting_for_height)
    await message.answer("Шаг 4/12: Рост (см).")


@router.message(QuickDiagnosticsStates.waiting_for_height)
async def quick_height(message: Message, state: FSMContext) -> None:
    value = _to_number(message.text or "")
    if value is None:
        await message.answer("Введите рост числом в см, например: 172")
        return
    await state.update_data(height_cm=value)
    await state.set_state(QuickDiagnosticsStates.waiting_for_weight)
    await message.answer("Шаг 5/12: Вес (кг).")


@router.message(QuickDiagnosticsStates.waiting_for_weight)
async def quick_weight(message: Message, state: FSMContext) -> None:
    value = _to_number(message.text or "")
    if value is None:
        await message.answer("Введите вес числом в кг, например: 68")
        return
    await state.update_data(weight_kg=value)
    await state.set_state(QuickDiagnosticsStates.waiting_for_waist)
    await message.answer("Шаг 6/12: Обхват талии (см).")


@router.message(QuickDiagnosticsStates.waiting_for_waist)
async def quick_waist(message: Message, state: FSMContext) -> None:
    value = _to_number(message.text or "")
    if value is None:
        await message.answer("Введите обхват талии числом в см.")
        return
    await state.update_data(waist_cm=value)
    await state.set_state(QuickDiagnosticsStates.waiting_for_hips)
    await message.answer("Шаг 7/12: Обхват бёдер (см).")


@router.message(QuickDiagnosticsStates.waiting_for_hips)
async def quick_hips(message: Message, state: FSMContext) -> None:
    value = _to_number(message.text or "")
    if value is None:
        await message.answer("Введите обхват бёдер числом в см.")
        return
    await state.update_data(hips_cm=value)
    await state.set_state(QuickDiagnosticsStates.waiting_for_chest)
    await message.answer("Шаг 8/12: Обхват груди (см).")


@router.message(QuickDiagnosticsStates.waiting_for_chest)
async def quick_chest(message: Message, state: FSMContext) -> None:
    value = _to_number(message.text or "")
    if value is None:
        await message.answer("Введите обхват груди числом в см.")
        return
    await state.update_data(chest_cm=value)
    await state.set_state(QuickDiagnosticsStates.waiting_for_wrist)
    await message.answer("Шаг 9/12: Обхват запястья (см).")


@router.message(QuickDiagnosticsStates.waiting_for_wrist)
async def quick_wrist(message: Message, state: FSMContext) -> None:
    value = _to_number(message.text or "")
    if value is None:
        await message.answer("Введите обхват запястья числом в см.")
        return
    await state.update_data(wrist_cm=value)
    await state.set_state(QuickDiagnosticsStates.waiting_for_sitting_height)
    await message.answer(
        "Шаг 10/12: Рост сидя (см, опционально).",
        reply_markup=get_scenario_skip_keyboard(),
    )


@router.message(QuickDiagnosticsStates.waiting_for_sitting_height, F.text == BUTTON_SKIP)
async def quick_skip_sitting_height(message: Message, state: FSMContext) -> None:
    await state.update_data(sitting_height_cm=None)
    await state.set_state(QuickDiagnosticsStates.waiting_for_goal)
    await message.answer(
        "Шаг 11/12: Какая у вас цель?",
        reply_markup=get_scenario_nav_keyboard(),
    )


@router.message(QuickDiagnosticsStates.waiting_for_sitting_height)
async def quick_sitting_height(message: Message, state: FSMContext) -> None:
    value = _to_number(message.text or "")
    if value is None:
        await message.answer("Введите рост сидя числом в см или нажмите «Пропустить».")
        return
    await state.update_data(sitting_height_cm=value)
    await state.set_state(QuickDiagnosticsStates.waiting_for_goal)
    await message.answer(
        "Шаг 11/12: Какая у вас цель?",
        reply_markup=get_scenario_nav_keyboard(),
    )


@router.message(QuickDiagnosticsStates.waiting_for_goal)
async def quick_goal(message: Message, state: FSMContext) -> None:
    await state.update_data(goal=(message.text or "").strip())
    await state.set_state(QuickDiagnosticsStates.waiting_for_health)
    await message.answer("Шаг 12/12: Кратко про здоровье/ограничения.")


@router.message(QuickDiagnosticsStates.waiting_for_health)
async def quick_health(message: Message, state: FSMContext) -> None:
    health_text = (message.text or "").strip()
    data = await state.get_data()
    payload = {
        "flow": "quick",
        "name": data.get("name"),
        "age": data.get("age"),
        "gender": data.get("gender"),
        "height_cm": data.get("height_cm"),
        "weight_kg": data.get("weight_kg"),
        "waist_cm": data.get("waist_cm"),
        "hips_cm": data.get("hips_cm"),
        "chest_cm": data.get("chest_cm"),
        "wrist_cm": data.get("wrist_cm"),
        "sitting_height_cm": data.get("sitting_height_cm"),
        "goal": data.get("goal"),
        "health": health_text,
    }

    user_id = await _get_or_create_user_id(message)
    found_factors = _find_stop_factors(health_text)
    payload["stop_factors"] = found_factors

    db = Database()
    diagnosis_session_id = db.save_diagnosis_session_and_calculation(
        user_id=user_id,
        session_payload=payload,
        calculation_payload={"status": "stopped" if found_factors else "completed"},
    )

    try:
        await send_diagnostics_summary(
            bot=message.bot,
            user_id=user_id,
            lead_id=diagnosis_session_id,
            payload=payload,
            title="Новая быстрая диагностика",
            lead_type="diagnosis",
        )
    except Exception:
        pass

    await state.clear()
    if found_factors:
        await message.answer(SAFE_STOP_MESSAGE, reply_markup=get_main_menu_keyboard())
        return

    await message.answer(
        "Спасибо! Быстрая диагностика сохранена.",
        reply_markup=get_main_menu_keyboard(),
    )


@router.callback_query(F.data == "diag:full")
async def start_full_questionnaire(callback: CallbackQuery, state: FSMContext) -> None:
    """Start full questionnaire flow."""
    if not callback.message:
        await callback.answer()
        return

    await state.clear()
    await state.set_state(FullQuestionnaireStates.waiting_for_name)
    await callback.message.answer(
        "Полная анкета. Шаг 1/18: Как вас зовут?",
        reply_markup=get_scenario_nav_keyboard(),
    )
    await callback.answer()


@router.message(StateFilter(FullQuestionnaireStates), F.text == BUTTON_BACK)
async def full_back_to_start(message: Message, state: FSMContext) -> None:
    """Safe back action for full flow (fallback to first step)."""
    await state.clear()
    await state.set_state(FullQuestionnaireStates.waiting_for_name)
    await message.answer(
        "Возвращаю к началу полной анкеты. Шаг 1/18: Как вас зовут?",
        reply_markup=get_scenario_nav_keyboard(),
    )


@router.message(FullQuestionnaireStates.waiting_for_name)
async def full_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=(message.text or "").strip())
    await state.set_state(FullQuestionnaireStates.waiting_for_age)
    await message.answer("Шаг 2/18: Возраст (полных лет).")


@router.message(FullQuestionnaireStates.waiting_for_age)
async def full_age(message: Message, state: FSMContext) -> None:
    value = _to_number(message.text or "")
    if value is None:
        await message.answer("Введите возраст числом.")
        return
    await state.update_data(age=int(value))
    await state.set_state(FullQuestionnaireStates.waiting_for_gender)
    await message.answer("Шаг 3/18: Пол.")


@router.message(FullQuestionnaireStates.waiting_for_gender)
async def full_gender(message: Message, state: FSMContext) -> None:
    await state.update_data(gender=(message.text or "").strip())
    await state.set_state(FullQuestionnaireStates.waiting_for_height)
    await message.answer("Шаг 4/18: Рост (см).")


@router.message(FullQuestionnaireStates.waiting_for_height)
async def full_height(message: Message, state: FSMContext) -> None:
    value = _to_number(message.text or "")
    if value is None:
        await message.answer("Введите рост числом.")
        return
    await state.update_data(height_cm=value)
    await state.set_state(FullQuestionnaireStates.waiting_for_weight)
    await message.answer("Шаг 5/18: Вес (кг).")


@router.message(FullQuestionnaireStates.waiting_for_weight)
async def full_weight(message: Message, state: FSMContext) -> None:
    value = _to_number(message.text or "")
    if value is None:
        await message.answer("Введите вес числом.")
        return
    await state.update_data(weight_kg=value)
    await state.set_state(FullQuestionnaireStates.waiting_for_city)
    await message.answer("Шаг 6/18: Город проживания.")


@router.message(FullQuestionnaireStates.waiting_for_city)
async def full_city(message: Message, state: FSMContext) -> None:
    await state.update_data(city=(message.text or "").strip())
    await state.set_state(FullQuestionnaireStates.waiting_for_occupation)
    await message.answer("Шаг 7/18: Род деятельности/профессия.")


@router.message(FullQuestionnaireStates.waiting_for_occupation)
async def full_occupation(message: Message, state: FSMContext) -> None:
    await state.update_data(occupation=(message.text or "").strip())
    await state.set_state(FullQuestionnaireStates.waiting_for_chronic_conditions)
    await message.answer("Шаг 8/18: Хронические заболевания (если нет — напишите «нет»).")


@router.message(FullQuestionnaireStates.waiting_for_chronic_conditions)
async def full_chronic(message: Message, state: FSMContext) -> None:
    await state.update_data(chronic_conditions=(message.text or "").strip())
    await state.set_state(FullQuestionnaireStates.waiting_for_injuries)
    await message.answer("Шаг 9/18: Текущие травмы/боли (если нет — «нет»).")


@router.message(FullQuestionnaireStates.waiting_for_injuries)
async def full_injuries(message: Message, state: FSMContext) -> None:
    await state.update_data(injuries=(message.text or "").strip())
    await state.set_state(FullQuestionnaireStates.waiting_for_surgeries)
    await message.answer("Шаг 10/18: Операции за последние 2 года.")


@router.message(FullQuestionnaireStates.waiting_for_surgeries)
async def full_surgeries(message: Message, state: FSMContext) -> None:
    await state.update_data(surgeries=(message.text or "").strip())
    await state.set_state(FullQuestionnaireStates.waiting_for_medications)
    await message.answer("Шаг 11/18: Постоянный приём лекарств/терапия.")


@router.message(FullQuestionnaireStates.waiting_for_medications)
async def full_medications(message: Message, state: FSMContext) -> None:
    await state.update_data(medications=(message.text or "").strip())
    await state.set_state(FullQuestionnaireStates.waiting_for_sleep_hours)
    await message.answer("Шаг 12/18: Сон в среднем (часов в сутки).")


@router.message(FullQuestionnaireStates.waiting_for_sleep_hours)
async def full_sleep(message: Message, state: FSMContext) -> None:
    value = _to_number(message.text or "")
    if value is None:
        await message.answer("Введите количество часов сна числом.")
        return
    await state.update_data(sleep_hours=value)
    await state.set_state(FullQuestionnaireStates.waiting_for_stress_level)
    await message.answer("Шаг 13/18: Уровень стресса (низкий/средний/высокий).")


@router.message(FullQuestionnaireStates.waiting_for_stress_level)
async def full_stress(message: Message, state: FSMContext) -> None:
    await state.update_data(stress_level=(message.text or "").strip())
    await state.set_state(FullQuestionnaireStates.waiting_for_experience)
    await message.answer("Шаг 14/18: Опыт тренировок.")


@router.message(FullQuestionnaireStates.waiting_for_experience)
async def full_experience(message: Message, state: FSMContext) -> None:
    await state.update_data(experience=(message.text or "").strip())
    await state.set_state(FullQuestionnaireStates.waiting_for_activity_level)
    await message.answer("Шаг 15/18: Уровень бытовой активности.")


@router.message(FullQuestionnaireStates.waiting_for_activity_level)
async def full_activity(message: Message, state: FSMContext) -> None:
    await state.update_data(activity_level=(message.text or "").strip())
    await state.set_state(FullQuestionnaireStates.waiting_for_workouts_per_week)
    await message.answer("Шаг 16/18: Сколько тренировок в неделю готовы делать?")


@router.message(FullQuestionnaireStates.waiting_for_workouts_per_week)
async def full_workouts(message: Message, state: FSMContext) -> None:
    value = _to_number(message.text or "")
    if value is None:
        await message.answer("Введите число тренировок в неделю.")
        return
    await state.update_data(workouts_per_week=int(value))
    await state.set_state(FullQuestionnaireStates.waiting_for_equipment)
    await message.answer("Шаг 17/18: Какой инвентарь доступен дома/в зале?")


@router.message(FullQuestionnaireStates.waiting_for_equipment)
async def full_equipment(message: Message, state: FSMContext) -> None:
    await state.update_data(equipment=(message.text or "").strip())
    await state.set_state(FullQuestionnaireStates.waiting_for_goal)
    await message.answer("Шаг 18/18: Главная фитнес-цель.")


@router.message(FullQuestionnaireStates.waiting_for_goal)
async def finish_full_questionnaire(message: Message, state: FSMContext) -> None:
    await state.update_data(goal=(message.text or "").strip())
    data = await state.get_data()

    payload = {"flow": "full", **data}
    risk_source_text = " ".join(
        str(data.get(field, "")) for field in ("chronic_conditions", "injuries", "medications")
    )
    found_factors = _find_stop_factors(risk_source_text)
    payload["stop_factors"] = found_factors

    user_id = await _get_or_create_user_id(message)
    db = Database()
    questionnaire_id = db.save_full_questionnaire(user_id=user_id, answers_payload=payload)

    try:
        await send_diagnostics_summary(
            bot=message.bot,
            user_id=user_id,
            lead_id=questionnaire_id,
            payload=payload,
            title="Новая полная анкета",
            lead_type="questionnaire",
        )
    except Exception:
        pass

    await state.clear()
    if found_factors:
        await message.answer(SAFE_STOP_MESSAGE, reply_markup=get_main_menu_keyboard())
        return

    await message.answer(
        "Спасибо! Полная анкета сохранена.",
        reply_markup=get_main_menu_keyboard(),
    )
