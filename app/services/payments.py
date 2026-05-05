"""Payment service helpers for Telegram invoices."""

from __future__ import annotations

from aiogram.types import LabeledPrice, Message

from app.config import load_settings
from app.db import Database

DONATION_MIN_AMOUNT = 300
CURRENCY = "RUB"

HIDDEN_PAYMENT_OFFERS: dict[str, dict[str, str | int]] = {
    "pay_1500": {
        "title": "Консультация / разбор",
        "description": "Оплата услуги фитнес-тренера",
        "amount_rub": 1500,
        "payload": "fitness_pay_1500",
    },
    "pay_12000": {
        "title": "Персональное сопровождение",
        "description": "Оплата услуги фитнес-тренера",
        "amount_rub": 12000,
        "payload": "fitness_pay_12000",
    },
}


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


async def send_hidden_payment_offer(message: Message, offer_key: str) -> bool:
    """Send hidden payment invoice for deep-link offer key."""
    offer = HIDDEN_PAYMENT_OFFERS.get(offer_key)
    if not offer:
        return False

    settings = load_settings()
    if not settings.provider_token:
        raise RuntimeError("PROVIDER_TOKEN is not configured")

    amount_rub = int(offer["amount_rub"])
    amount_kopecks = amount_rub * 100

    short_text = (
        "Оплата услуги — 1 500 ₽"
        if offer_key == "pay_1500"
        else "Оплата сопровождения — 12 000 ₽"
    )
    await message.answer(short_text)
    await message.bot.send_invoice(
        chat_id=message.chat.id,
        title=str(offer["title"]),
        description=str(offer["description"]),
        payload=str(offer["payload"]),
        provider_token=settings.provider_token,
        currency=CURRENCY,
        prices=[LabeledPrice(label=str(offer["title"]), amount=amount_kopecks)],
        start_parameter=offer_key,
    )
    return True
