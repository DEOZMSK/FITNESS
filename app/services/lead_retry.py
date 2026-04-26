"""Retry unsent admin leads at application startup."""

from __future__ import annotations

import logging

from aiogram import Bot

from app.db import Database
from app.services.admin_notify import send_diagnostics_summary, send_payment_event

logger = logging.getLogger(__name__)


async def retry_unsent_leads(bot: Bot) -> None:
    """Retry admin notifications for leads with lead_sent = 0."""
    db = Database()

    for lead in db.get_unsent_diagnosis_leads():
        try:
            await send_diagnostics_summary(
                bot=bot,
                user_id=int(lead["user_id"]),
                lead_id=int(lead["lead_id"]),
                payload=dict(lead.get("payload") or {}),
                title="Повторная отправка: диагностика",
                lead_type="diagnosis",
                telegram_user_id=lead.get("telegram_user_id"),
                telegram_username=lead.get("telegram_username"),
            )
            db.mark_diagnosis_lead_sent(int(lead["lead_id"]))
        except Exception:
            logger.exception("Retry failed for diagnosis lead id=%s", lead.get("lead_id"))

    for lead in db.get_unsent_questionnaire_leads():
        try:
            await send_diagnostics_summary(
                bot=bot,
                user_id=int(lead["user_id"]),
                lead_id=int(lead["lead_id"]),
                payload=dict(lead.get("payload") or {}),
                title="Повторная отправка: расширенная анкета здоровья",
                lead_type="questionnaire",
                telegram_user_id=lead.get("telegram_user_id"),
                telegram_username=lead.get("telegram_username"),
            )
            db.mark_questionnaire_lead_sent(int(lead["lead_id"]))
        except Exception:
            logger.exception("Retry failed for questionnaire lead id=%s", lead.get("lead_id"))

    for payment in db.get_unsent_payment_leads():
        try:
            payload = dict(payment.get("payload") or {})
            await send_payment_event(
                bot=bot,
                user_id=int(payment["user_id"]),
                payment_id=int(payment["payment_id"]),
                amount_rub=int(payment["amount"]),
                purpose=str(payload.get("purpose") or "payment"),
            )
            db.mark_payment_lead_sent(int(payment["payment_id"]))
        except Exception:
            logger.exception("Retry failed for payment id=%s", payment.get("payment_id"))
