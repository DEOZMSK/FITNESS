"""Admin notifications with delivery fallback flags in DB."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from html import escape
from typing import Any

from aiogram import Bot

from app.config import load_settings
from app.db import Database

logger = logging.getLogger(__name__)


def _stringify_value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Да" if value else "Нет"
    return str(value)


def _format_item(label: str, value: Any) -> str:
    return f"• <b>{escape(label)}</b>: <code>{escape(_stringify_value(value))}</code>"


def _format_section(title: str, items: list[tuple[str, Any]]) -> list[str]:
    lines = [f"<b>{escape(title)}</b>"]
    lines.extend(_format_item(label, value) for label, value in items)
    return lines


def _collect_diagnostics_sections(payload: dict[str, Any]) -> list[str]:
    profile_items = [
        ("Имя", payload.get("name")),
        ("Возраст", payload.get("age")),
        ("Пол", payload.get("gender")),
    ]
    questionnaire_items = [
        ("Цель", payload.get("goal")),
        ("Давление", payload.get("pressure")),
        ("Здоровье / ограничения", payload.get("health")),
        ("Хронические заболевания", payload.get("chronic_conditions")),
        ("Травмы", payload.get("injuries")),
        ("Операции (6 мес)", payload.get("surgeries_6m")),
        ("Лекарства", payload.get("medications")),
        ("Сон (ч/сут)", payload.get("sleep_hours")),
        ("Стресс (1-10)", payload.get("stress_level")),
        ("Активность", payload.get("activity_level")),
        ("Тренировок в неделю", payload.get("workouts_per_week")),
        ("Инвентарь", payload.get("equipment")),
    ]
    measurements_items = [
        ("Рост (см)", payload.get("height_cm")),
        ("Вес (кг)", payload.get("weight_kg")),
        ("Талия (см)", payload.get("waist_cm")),
        ("Бёдра (см)", payload.get("hips_cm")),
        ("Грудь (см)", payload.get("chest_cm")),
        ("Запястье (см)", payload.get("wrist_cm")),
        ("Сидячая высота (см)", payload.get("sitting_height_cm")),
    ]
    calculations_raw = payload.get("calculations")
    calculations_items = []
    if isinstance(calculations_raw, dict):
        label_map = {
            "status": "Статус",
            "bmi": "BMI",
            "bmr_mifflin": "Базовый обмен (Mifflin)",
            "tdee": "TDEE",
            "fat_percent_navy": "Жир (%) по Navy",
            "waist_to_height_ratio": "Талия/рост",
            "activity_factor": "Коэффициент активности",
            "calories_target": "Целевая калорийность",
            "protein_g": "Белки (г)",
            "fat_g": "Жиры (г)",
            "carbs_g": "Углеводы (г)",
        }
        calculations_items = [
            (label_map.get(key, key.replace("_", " ").title()), value)
            for key, value in calculations_raw.items()
        ]

    stop_factors = payload.get("stop_factors")
    stop_text = "Нет"
    if isinstance(stop_factors, list) and stop_factors:
        stop_text = "; ".join(str(item) for item in stop_factors)

    source_items = [
        (
            "Тип анкеты",
            "Экспресс-расчёт метрик"
            if payload.get("flow") == "quick"
            else "Расширенная анкета здоровья",
        )
    ]

    lines: list[str] = []
    lines.extend(_format_section("Пользователь", profile_items))
    lines.append("")
    lines.extend(_format_section("Анкета", questionnaire_items))
    lines.append("")
    lines.extend(_format_section("Замеры", measurements_items))
    lines.append("")
    lines.extend(_format_section("Расчёты", calculations_items or [("Данные расчётов", "—")]))
    lines.append("")
    lines.extend(_format_section("Стоп-факторы", [("Найдено", stop_text)]))
    lines.append("")
    lines.extend(_format_section("Источник", source_items))
    return lines


async def send_diagnostics_summary(
    *,
    bot: Bot,
    user_id: int,
    lead_id: int,
    payload: dict[str, Any],
    title: str,
    lead_type: str = "diagnosis",
    telegram_user_id: int | None = None,
    telegram_username: str | None = None,
) -> None:
    """Send diagnostics summary to admin. On failure mark lead as unsent."""
    settings = load_settings()
    payload_for_admin = dict(payload)
    calculations = payload_for_admin.pop("calculations", None)
    if calculations is not None:
        payload_for_admin["calculations"] = calculations

    lines = [
        f"<b>{escape(title)}</b>",
        f"User ID: <code>{user_id}</code>",
        f"Telegram User ID: <code>{telegram_user_id if telegram_user_id is not None else '—'}</code>",
        f"Telegram username: <code>{escape(telegram_username or '—')}</code>",
        "",
        *_collect_diagnostics_sections(payload_for_admin),
    ]
    db = Database()
    try:
        await bot.send_message(settings.admin_id, "\n".join(lines), parse_mode="HTML")
    except Exception:
        if lead_type == "questionnaire":
            db.mark_questionnaire_lead_unsent(lead_id)
        else:
            db.mark_diagnosis_lead_unsent(lead_id)
        logger.exception("Failed to send diagnostics summary to admin")
        raise


async def send_payment_event(
    *,
    bot: Bot,
    user_id: int,
    payment_id: int,
    amount_rub: int,
    purpose: str,
) -> None:
    """Send payment event to admin. On failure mark lead as unsent."""
    settings = load_settings()
    paid_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    text = "\n".join(
        [
            "<b>Новая оплата</b>",
            f"User ID: <code>{user_id}</code>",
            f"• <b>Сумма</b>: {amount_rub} RUB",
            f"• <b>Дата</b>: {paid_at}",
            f"• <b>Назначение</b>: {purpose}",
        ]
    )
    db = Database()
    try:
        await bot.send_message(settings.admin_id, text, parse_mode="HTML")
    except Exception:
        db.mark_payment_lead_unsent(payment_id)
        logger.exception("Failed to send payment event to admin")
        raise
