"""Admin notifications with delivery fallback flags in DB."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from aiogram import Bot

from app.config import load_settings
from app.db import Database

logger = logging.getLogger(__name__)


def _format_payload_lines(payload: dict[str, Any]) -> list[str]:
    return [f"• <b>{key}</b>: {value}" for key, value in payload.items()]


async def send_diagnostics_summary(
    *,
    bot: Bot,
    user_id: int,
    lead_id: int,
    payload: dict[str, Any],
    title: str,
    lead_type: str = "diagnosis",
) -> None:
    """Send diagnostics summary to admin. On failure mark lead as unsent."""
    settings = load_settings()
    lines = [f"<b>{title}</b>", f"User ID: <code>{user_id}</code>", *_format_payload_lines(payload)]
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
