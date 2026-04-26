"""Handlers for viewing user diagnosis results."""

from __future__ import annotations

from datetime import datetime

from aiogram import F, Router
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from app.bot.handlers.diagnostics import show_diagnostics_menu_message
from app.bot.handlers.about import build_contacts_text
from app.bot.keyboards import BUTTON_HOME_MENU, BUTTON_RESULTS, get_contact_trainer_keyboard
from app.db import Database

router = Router(name=__name__)

BUTTON_RESTART_DIAG = "🔁 Пройти заново"
BUTTON_CONTACT_ALT = "💬 Написать тренеру"


def _results_actions_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BUTTON_RESTART_DIAG), KeyboardButton(text=BUTTON_CONTACT_ALT)],
            [KeyboardButton(text=BUTTON_HOME_MENU)],
        ],
        resize_keyboard=True,
    )


def _format_created_at(raw_value: object) -> str:
    if not isinstance(raw_value, str):
        return "—"
    try:
        return datetime.strptime(raw_value, "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return raw_value


def _build_results_text(payload: dict[str, object], calculations: dict[str, object], created_at: object) -> str:
    def _metric_value(key: str, status_key: str | None = None, suffix: str = "") -> str:
        value = calculations.get(key)
        if value is None:
            return "не рассчитывался в этом сценарии"
        if status_key:
            status = calculations.get(status_key)
            if status is None:
                return f"{value}{suffix}"
            return f"{value}{suffix} ({status})"
        return f"{value}{suffix}"

    macros = calculations.get("macros")
    if isinstance(macros, dict):
        bju_value = (
            f"Б {macros.get('protein_g', '—')} г / "
            f"Ж {macros.get('fat_g', '—')} г / "
            f"У {macros.get('carbs_g', '—')} г"
        )
    else:
        bju_value = "не рассчитывался в этом сценарии"

    lines = [
        "📊 <b>Ваши последние результаты</b>",
        f"📅 Дата: {_format_created_at(created_at)}",
        "",
        "📈 <b>Ключевые метрики</b>",
        f"• ИМТ (BMI): {_metric_value('bmi', 'bmi_status')}",
        f"• WHR: {_metric_value('whr', 'whr_status')}",
        f"• BMR: {_metric_value('bmr', suffix=' ккал/сутки')}",
        f"• БЖУ: {bju_value}",
        f"• Идеальный вес: {_metric_value('ideal_weight_kg', suffix=' кг')}",
        f"• Цель: {payload.get('goal', '—')}",
    ]

    health = payload.get("health")
    stop_factors = payload.get("stop_factors")
    restrictions_line = "• Ограничения: "

    if isinstance(stop_factors, list) and stop_factors:
        restrictions_line += ", ".join(str(factor) for factor in stop_factors)
    elif isinstance(health, str) and health.strip():
        restrictions_line += health.strip()
    else:
        restrictions_line += "не указаны"

    lines.extend(["", "⚠️ <b>Ограничения</b>", restrictions_line])
    lines.extend(
        [
            "",
            "ℹ️ <b>Что означают метрики</b>",
            "• ИМТ (BMI): соотношение роста и веса, общий ориентир по массе тела.",
            "• WHR: отношение талии к бёдрам, косвенный индикатор распределения жира.",
            "• BMR: базовый обмен — энергия, которую организм тратит в покое.",
            "• БЖУ: суточное распределение белков, жиров и углеводов.",
            "• Идеальный вес: ориентировочный диапазон/оценка по формулам, не медицинский диагноз.",
        ]
    )
    return "\n".join(lines)


@router.message(F.text == BUTTON_RESULTS)
async def show_latest_results(message: Message) -> None:
    if not message.from_user:
        await message.answer("Не удалось определить пользователя. Попробуйте позже.")
        return

    db = Database()
    user_id = db.upsert_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
    latest_result = db.get_latest_diagnosis_result(user_id=user_id)

    if latest_result is None:
        await message.answer(
            "Результатов пока нет. Пройдите диагностику — и я покажу отчёт здесь.",
            reply_markup=_results_actions_keyboard(),
        )
        return

    payload = latest_result.get("session_payload", {})
    calculations = latest_result.get("calculation_payload", {})
    saved_user_report_text = latest_result.get("user_report_text")
    if isinstance(saved_user_report_text, str) and saved_user_report_text.strip():
        date_line = f"📅 Дата: {_format_created_at(latest_result.get('session_created_at'))}"
        text = f"📊 <b>Ваши последние результаты</b>\n{date_line}\n\n{saved_user_report_text}"
    else:
        text = _build_results_text(
            payload=payload if isinstance(payload, dict) else {},
            calculations=calculations if isinstance(calculations, dict) else {},
            created_at=latest_result.get("session_created_at"),
        )
    await message.answer(text, reply_markup=_results_actions_keyboard())


@router.message(F.text == BUTTON_RESTART_DIAG)
async def restart_diagnostics_from_results(message: Message) -> None:
    await show_diagnostics_menu_message(message)


@router.message(F.text == BUTTON_CONTACT_ALT)
async def open_contact_from_results(message: Message) -> None:
    await message.answer(build_contacts_text(), reply_markup=get_contact_trainer_keyboard())
