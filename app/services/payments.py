"""Payment service helpers for Telegram invoices."""

from __future__ import annotations

from aiogram.types import LabeledPrice, Message

from app.config import load_settings
from app.db import Database

DONATION_MIN_AMOUNT = 300


def validate_amount(amount: int) -> None:
    """Validate minimal donation amount."""
    if amount < DONATION_MIN_AMOUNT:
        raise ValueError(f"Минимальная сумма доната — {DONATION_MIN_AMOUNT} ₽.")


async def create_invoice(message: Message, amount_rub: int) -> int:
    """Create Telegram invoice and save payment event as created."""
    validate_amount(amount_rub)

    if not message.from_user:
        raise RuntimeError("Message does not contain user")

    settings = load_settings()
    db = Database()
    user_id = db.upsert_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
    payment_id = db.record_payment(
        user_id=user_id,
        amount=amount_rub,
        currency="RUB",
        status="invoice_created",
        payload={
            "telegram_user_id": message.from_user.id,
            "chat_id": message.chat.id,
            "purpose": "donation",
            "shop_id": settings.shop_id,
        },
    )

    await message.bot.send_invoice(
        chat_id=message.chat.id,
        title="Донат тренеру",
        description="Поддержка фитнес-проекта",
        payload=f"donation:{payment_id}",
        provider_token=settings.provider_token,
        currency="RUB",
        prices=[LabeledPrice(label="Донат", amount=amount_rub * 100)],
        start_parameter="fitness-donation",
    )
    return payment_id
