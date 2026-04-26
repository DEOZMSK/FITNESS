"""Handlers for quick diagnostics and full questionnaire."""

from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

from app.calculators.body_metrics import (
    bmi,
    bmi_interpretation,
    ideal_weight,
    ideal_weight_by_body_type,
    whr,
    whr_interpretation,
)
from app.calculators.calories import bju_distribution, bmr
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


def _diagnostics_cta_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💬 Написать тренеру"), KeyboardButton(text="📊 Мои результаты")],
            [KeyboardButton(text="🏠 Главное меню")],
        ],
        resize_keyboard=True,
    )


def _build_quick_calculations(payload: dict[str, object]) -> dict[str, object]:
    calculations: dict[str, object] = {}
    try:
        sex = str(payload.get("gender", ""))
        height_cm = float(payload["height_cm"])
        weight_kg = float(payload["weight_kg"])
        age = int(payload["age"])
        waist_cm = float(payload["waist_cm"])
        hips_cm = float(payload["hips_cm"])

        bmi_value = bmi(height_cm=height_cm, weight_kg=weight_kg)
        whr_value = whr(waist_cm=waist_cm, hip_cm=hips_cm)
        bmr_value = bmr(weight_kg=weight_kg, height_cm=height_cm, age=age, sex=sex)
        macros = bju_distribution(weight_kg=weight_kg, calories_target=round(bmr_value), goal="maintain")

        ideal_weight_estimate = ideal_weight_by_body_type(
            height_cm=height_cm,
            sex=sex,
            body_type=str(payload.get("body_type", "")),
        )

        calculations = {
            "bmi": bmi_value,
            "bmi_status": bmi_interpretation(bmi_value, age),
            "whr": whr_value,
            "whr_status": whr_interpretation(whr_value, sex),
            "ideal_weight_kg": ideal_weight_estimate,
            "bmr": bmr_value,
            "macros": macros,
        }
    except (ValueError, KeyError, TypeError):
        calculations = {"status": "failed"}

    return calculations


def _build_quick_report_text(payload: dict[str, object], calculations: dict[str, object]) -> str:
    ideal_weight_value = calculations.get("ideal_weight_kg")
    if isinstance(ideal_weight_value, tuple):
        ideal_weight_text = f"{ideal_weight_value[0]}–{ideal_weight_value[1]} кг"
    else:
        ideal_weight_text = f"{ideal_weight_value} кг"

    user_data_block = (
        "👤 <b>Данные пользователя</b>\n"
        f"• Имя: {payload.get('name', '—')}\n"
        f"• Возраст: {payload.get('age', '—')}\n"
        f"• Пол: {payload.get('gender', '—')}\n"
        f"• Рост/вес: {payload.get('height_cm', '—')} см / {payload.get('weight_kg', '—')} кг\n"
        f"• Цель: {payload.get('goal', '—')}"
    )

    if calculations.get("status") == "failed":
        calculations_block = "📈 <b>Расчёты</b>\n• Не удалось рассчитать автоматически. Тренер проверит вручную."
    else:
        macros = calculations.get("macros", {})
        calculations_block = (
            "📈 <b>Расчёты</b>\n"
            f"• ИМТ: {calculations.get('bmi')} ({calculations.get('bmi_status')})\n"
            f"• WHR: {calculations.get('whr')} ({calculations.get('whr_status')})\n"
            f"• Идеальный вес (оценка): {ideal_weight_text}\n"
            f"• BMR: {calculations.get('bmr')} ккал/сутки\n"
            f"• БЖУ (поддержание): Б {macros.get('protein_g')} г / "
            f"Ж {macros.get('fat_g')} г / У {macros.get('carbs_g')} г"
        )

    warning_block = (
        "⚠️ <b>Важное предупреждение</b>\n"
        "Эти расчёты носят ориентировочный характер и не заменяют консультацию врача."
    )

    discussion_block = (
        "🤝 <b>Обсуждение с тренером</b>\n"
        "На разборе уточним самочувствие, ограничения и безопасный стартовый план."
    )

    cta_block = (
        "💬 <b>Готовы продолжить?</b>\n"
        "Если хотите, мягко двигаемся дальше: тренер поможет разобрать результаты и выбрать комфортный следующий шаг."
    )

    return "\n\n".join([user_data_block, calculations_block, warning_block, discussion_block, cta_block])


def _build_full_calculations(payload: dict[str, object]) -> dict[str, object]:
    try:
        sex = str(payload.get("gender", ""))
        height_cm = float(payload["height_cm"])
        weight_kg = float(payload["weight_kg"])
        age = int(payload["age"])
        bmi_value = bmi(height_cm=height_cm, weight_kg=weight_kg)
        bmr_value = bmr(weight_kg=weight_kg, height_cm=height_cm, age=age, sex=sex)
        return {
            "bmi": bmi_value,
            "bmi_status": bmi_interpretation(bmi_value, age),
            "ideal_weight_kg": ideal_weight(height_cm=height_cm, sex=sex),
            "bmr": bmr_value,
        }
    except (ValueError, KeyError, TypeError):
        return {"status": "failed"}


def _build_full_report_text(payload: dict[str, object], calculations: dict[str, object]) -> str:
    user_data_block = (
        "👤 <b>Данные пользователя</b>\n"
        f"• Имя: {payload.get('name', '—')}\n"
        f"• Возраст: {payload.get('age', '—')}\n"
        f"• Пол: {payload.get('gender', '—')}\n"
        f"• Рост/вес: {payload.get('height_cm', '—')} см / {payload.get('weight_kg', '—')} кг\n"
        f"• Цель: {payload.get('goal', '—')}"
    )
    if calculations.get("status") == "failed":
        calculations_block = "📈 <b>Расчёты</b>\n• Недостаточно данных для автоматических расчётов."
    else:
        calculations_block = (
            "📈 <b>Расчёты</b>\n"
            f"• ИМТ: {calculations.get('bmi')} ({calculations.get('bmi_status')})\n"
            f"• Идеальный вес (оценка): {calculations.get('ideal_weight_kg')} кг\n"
            f"• BMR: {calculations.get('bmr')} ккал/сутки"
        )
    warning_block = (
        "⚠️ <b>Важное предупреждение</b>\n"
        "Анкета и расчёты не заменяют медицинскую консультацию, особенно при болях и хронических состояниях."
    )
    discussion_block = (
        "🤝 <b>Обсуждение с тренером</b>\n"
        "На консультации определим приоритеты, ограничения и безопасную стратегию старта."
    )
    cta_block = (
        "💬 <b>Готовы продолжить?</b>\n"
        "Можно мягко перейти к следующему шагу: тренер поможет адаптировать план под ваш ритм жизни."
    )
    return "\n\n".join([user_data_block, calculations_block, warning_block, discussion_block, cta_block])


def _to_number(raw_value: str) -> float | None:
    value = raw_value.replace(",", ".").strip()
    try:
        parsed = float(value)
    except ValueError:
        return None
    if parsed <= 0:
        return None
    return parsed


def _to_blood_pressure(raw_value: str) -> tuple[int, int] | None:
    match = re.fullmatch(r"\s*(\d{2,3})\s*[/\\\-\s]\s*(\d{2,3})\s*", raw_value)
    if not match:
        return None
    systolic = int(match.group(1))
    diastolic = int(match.group(2))
    if systolic <= diastolic:
        return None
    if not (70 <= systolic <= 250 and 40 <= diastolic <= 150):
        return None
    return systolic, diastolic


def _is_in_range(value: float, min_value: float, max_value: float) -> bool:
    return min_value <= value <= max_value


def _hips_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Оставить", callback_data="diag:hips:keep"),
                InlineKeyboardButton(text="✏️ Ввести заново", callback_data="diag:hips:retry"),
            ]
        ]
    )


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
        "Быстрая диагностика. Шаг 1/13: Как вас зовут?",
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
        "Возвращаю к началу быстрой диагностики. Шаг 1/13: Как вас зовут?",
        reply_markup=get_scenario_nav_keyboard(),
    )


@router.message(QuickDiagnosticsStates.waiting_for_name)
async def quick_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=(message.text or "").strip())
    await state.set_state(QuickDiagnosticsStates.waiting_for_age)
    await message.answer("Шаг 2/13: Укажите возраст (полных лет).")


@router.message(QuickDiagnosticsStates.waiting_for_age)
async def quick_age(message: Message, state: FSMContext) -> None:
    value = _to_number(message.text or "")
    if value is None:
        await message.answer("Не разобрал возраст. Введите число, например: 29.")
        return
    if not _is_in_range(value, 10, 100):
        await message.answer("Похоже, возраст вне диапазона 10–100 лет. Попробуйте ещё раз.")
        return
    await state.update_data(age=int(value))
    await state.set_state(QuickDiagnosticsStates.waiting_for_gender)
    await message.answer("Шаг 3/13: Ваш пол?")


@router.message(QuickDiagnosticsStates.waiting_for_gender)
async def quick_gender(message: Message, state: FSMContext) -> None:
    await state.update_data(gender=(message.text or "").strip())
    await state.set_state(QuickDiagnosticsStates.waiting_for_height)
    await message.answer("Шаг 4/13: Рост (см).")


@router.message(QuickDiagnosticsStates.waiting_for_height)
async def quick_height(message: Message, state: FSMContext) -> None:
    value = _to_number(message.text or "")
    if value is None:
        await message.answer("Не разобрал рост. Введите число в см, например: 172.")
        return
    if not _is_in_range(value, 120, 230):
        await message.answer("Рост должен быть в диапазоне 120–230 см. Попробуйте ещё раз.")
        return
    await state.update_data(height_cm=value)
    await state.set_state(QuickDiagnosticsStates.waiting_for_weight)
    await message.answer("Шаг 5/13: Вес (кг).")


@router.message(QuickDiagnosticsStates.waiting_for_weight)
async def quick_weight(message: Message, state: FSMContext) -> None:
    value = _to_number(message.text or "")
    if value is None:
        await message.answer("Не разобрал вес. Введите число в кг, например: 68.")
        return
    if not _is_in_range(value, 30, 300):
        await message.answer("Вес должен быть в диапазоне 30–300 кг. Попробуйте ещё раз.")
        return
    await state.update_data(weight_kg=value)
    await state.set_state(QuickDiagnosticsStates.waiting_for_waist)
    await message.answer("Шаг 6/13: Обхват талии (см).")


@router.message(QuickDiagnosticsStates.waiting_for_waist)
async def quick_waist(message: Message, state: FSMContext) -> None:
    value = _to_number(message.text or "")
    if value is None:
        await message.answer("Не разобрал талию. Введите число в см.")
        return
    if not _is_in_range(value, 40, 200):
        await message.answer("Талия должна быть в диапазоне 40–200 см. Попробуйте ещё раз.")
        return
    await state.update_data(waist_cm=value)
    await state.set_state(QuickDiagnosticsStates.waiting_for_hips)
    await message.answer("Шаг 7/13: Обхват бёдер (см).")


@router.message(QuickDiagnosticsStates.waiting_for_hips)
async def quick_hips(message: Message, state: FSMContext) -> None:
    value = _to_number(message.text or "")
    if value is None:
        await message.answer("Не разобрал бёдра. Введите число в см.")
        return
    if not _is_in_range(value, 40, 220):
        await message.answer("Бёдра должны быть в диапазоне 40–220 см. Попробуйте ещё раз.")
        return
    data = await state.get_data()
    waist_cm = data.get("waist_cm")
    if isinstance(waist_cm, (int, float)) and value < float(waist_cm):
        await state.update_data(pending_hips_cm=value)
        await state.set_state(QuickDiagnosticsStates.waiting_for_hips_confirmation)
        await message.answer(
            "Бёдра меньше талии — такое бывает, но часто это просто опечатка. Оставляем так?",
            reply_markup=_hips_confirmation_keyboard(),
        )
        return
    await state.update_data(hips_cm=value)
    await state.set_state(QuickDiagnosticsStates.waiting_for_chest)
    await message.answer("Шаг 8/13: Обхват груди (см).")


@router.callback_query(
    QuickDiagnosticsStates.waiting_for_hips_confirmation,
    F.data.in_({"diag:hips:keep", "diag:hips:retry"}),
)
async def quick_hips_confirmation(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.message:
        await callback.answer()
        return

    if callback.data == "diag:hips:keep":
        data = await state.get_data()
        pending_hips_cm = data.get("pending_hips_cm")
        if not isinstance(pending_hips_cm, (int, float)):
            await state.set_state(QuickDiagnosticsStates.waiting_for_hips)
            await callback.message.answer("Не нашёл значение бёдер. Введите обхват бёдер ещё раз (см).")
            await callback.answer()
            return
        await state.update_data(hips_cm=float(pending_hips_cm), pending_hips_cm=None)
        await state.set_state(QuickDiagnosticsStates.waiting_for_chest)
        await callback.message.answer("Принято. Шаг 8/13: Обхват груди (см).")
        await callback.answer("Оставили текущее значение")
        return

    await state.update_data(pending_hips_cm=None)
    await state.set_state(QuickDiagnosticsStates.waiting_for_hips)
    await callback.message.answer("Хорошо, введите обхват бёдер заново (см).")
    await callback.answer("Введите значение заново")


@router.message(QuickDiagnosticsStates.waiting_for_chest)
async def quick_chest(message: Message, state: FSMContext) -> None:
    value = _to_number(message.text or "")
    if value is None:
        await message.answer("Не разобрал грудь. Введите число в см.")
        return
    if not _is_in_range(value, 50, 220):
        await message.answer("Грудь должна быть в диапазоне 50–220 см. Попробуйте ещё раз.")
        return
    await state.update_data(chest_cm=value)
    await state.set_state(QuickDiagnosticsStates.waiting_for_wrist)
    await message.answer("Шаг 9/13: Обхват запястья (см).")


@router.message(QuickDiagnosticsStates.waiting_for_wrist)
async def quick_wrist(message: Message, state: FSMContext) -> None:
    value = _to_number(message.text or "")
    if value is None:
        await message.answer("Не разобрал запястье. Введите число в см.")
        return
    if not _is_in_range(value, 10, 30):
        await message.answer("Запястье должно быть в диапазоне 10–30 см. Попробуйте ещё раз.")
        return
    await state.update_data(wrist_cm=value)
    await state.set_state(QuickDiagnosticsStates.waiting_for_sitting_height)
    await message.answer(
        "Шаг 10/13: Рост сидя (см, опционально).",
        reply_markup=get_scenario_skip_keyboard(),
    )


@router.message(QuickDiagnosticsStates.waiting_for_sitting_height, F.text == BUTTON_SKIP)
async def quick_skip_sitting_height(message: Message, state: FSMContext) -> None:
    await state.update_data(sitting_height_cm=None)
    await state.set_state(QuickDiagnosticsStates.waiting_for_pressure)
    await message.answer(
        "Шаг 11/13: Артериальное давление (например, 120/80, опционально).",
        reply_markup=get_scenario_skip_keyboard(),
    )


@router.message(QuickDiagnosticsStates.waiting_for_sitting_height)
async def quick_sitting_height(message: Message, state: FSMContext) -> None:
    value = _to_number(message.text or "")
    if value is None:
        await message.answer("Не разобрал рост сидя. Введите число в см или нажмите «Пропустить».")
        return
    if not _is_in_range(value, 50, 140):
        await message.answer("Рост сидя должен быть в диапазоне 50–140 см. Попробуйте ещё раз.")
        return
    await state.update_data(sitting_height_cm=value)
    await state.set_state(QuickDiagnosticsStates.waiting_for_pressure)
    await message.answer(
        "Шаг 11/13: Артериальное давление (например, 120/80, опционально).",
        reply_markup=get_scenario_skip_keyboard(),
    )


@router.message(QuickDiagnosticsStates.waiting_for_pressure, F.text == BUTTON_SKIP)
async def quick_skip_pressure(message: Message, state: FSMContext) -> None:
    await state.update_data(pressure=None)
    await state.set_state(QuickDiagnosticsStates.waiting_for_goal)
    await message.answer(
        "Шаг 12/13: Какая у вас цель?",
        reply_markup=get_scenario_nav_keyboard(),
    )


@router.message(QuickDiagnosticsStates.waiting_for_pressure)
async def quick_pressure(message: Message, state: FSMContext) -> None:
    pressure = _to_blood_pressure(message.text or "")
    if pressure is None:
        await message.answer(
            "Не разобрал давление. Введите в формате 120/80 или нажмите «Пропустить».",
            reply_markup=get_scenario_skip_keyboard(),
        )
        return
    await state.update_data(pressure=f"{pressure[0]}/{pressure[1]}")
    await state.set_state(QuickDiagnosticsStates.waiting_for_goal)
    await message.answer(
        "Шаг 12/13: Какая у вас цель?",
        reply_markup=get_scenario_nav_keyboard(),
    )


@router.message(QuickDiagnosticsStates.waiting_for_goal)
async def quick_goal(message: Message, state: FSMContext) -> None:
    await state.update_data(goal=(message.text or "").strip())
    await state.set_state(QuickDiagnosticsStates.waiting_for_health)
    await message.answer("Шаг 13/13: Кратко про здоровье/ограничения.")


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
        "pressure": data.get("pressure"),
        "goal": data.get("goal"),
        "health": health_text,
    }

    user_id = await _get_or_create_user_id(message)
    found_factors = _find_stop_factors(health_text)
    payload["stop_factors"] = found_factors

    calculations = _build_quick_calculations(payload)
    calculation_payload = {"status": "stopped" if found_factors else "completed", **calculations}

    db = Database()
    diagnosis_session_id = db.save_diagnosis_session_and_calculation(
        user_id=user_id,
        session_payload=payload,
        calculation_payload=calculation_payload,
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

    if found_factors:
        await state.clear()
        await message.answer(SAFE_STOP_MESSAGE, reply_markup=get_main_menu_keyboard())
        return

    report_text = _build_quick_report_text(payload=payload, calculations=calculations)
    await message.answer(report_text, reply_markup=_diagnostics_cta_keyboard())
    await message.answer(
        "Спасибо! Отчёт готов — можете обсудить его с тренером или вернуться в меню.",
        reply_markup=_diagnostics_cta_keyboard(),
    )
    await state.clear()


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
    calculations = _build_full_calculations(payload)

    user_id = await _get_or_create_user_id(message)
    db = Database()
    questionnaire_id = db.save_full_questionnaire(
        user_id=user_id,
        answers_payload={**payload, "calculations": calculations},
    )

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

    if found_factors:
        await state.clear()
        await message.answer(SAFE_STOP_MESSAGE, reply_markup=get_main_menu_keyboard())
        return

    report_text = _build_full_report_text(payload=payload, calculations=calculations)
    await message.answer(report_text, reply_markup=_diagnostics_cta_keyboard())
    await message.answer(
        "Спасибо! Полная анкета обработана, отчёт готов.",
        reply_markup=_diagnostics_cta_keyboard(),
    )
    await state.clear()
