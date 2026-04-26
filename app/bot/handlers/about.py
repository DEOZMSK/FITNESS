"""About router screens and donation FSM flow."""

import logging
from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    PreCheckoutQuery,
)

from app.bot.keyboards import get_contact_trainer_keyboard
from app.bot.states import DonateStates
from app.data.products import products
from app.data.reviews import reviews
from app.data.trainer_profile import trainer_profile
from app.db import Database
from app.services import DONATION_MIN_AMOUNT, create_invoice, send_payment_event

router = Router(name=__name__)
logger = logging.getLogger(__name__)
ABOUT_PHOTO_PATH = Path("/data/me.png")
TELEGRAM_CAPTION_LIMIT = 1024


def _about_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="about:menu")]]
    )


def _build_services_lines() -> list[str]:
    active_products = [item for item in products if item.get("is_active")]
    if not active_products:
        return ["Сейчас нет активных услуг."]

    lines: list[str] = []
    for item in active_products:
        lines.append(
            "\n".join(
                [
                    f"• <b>{item['name']}</b>",
                    str(item["description"]),
                    f"Формат: {item.get('format', '—')}",
                    f"Результат: {item.get('result', '—')}",
                    f"Стоимость: {item['price']} {item['currency']}",
                ]
            )
        )
    return lines


def _build_reviews_lines() -> list[str]:
    published_reviews = [item for item in reviews if item.get("is_published", True)]
    if not published_reviews:
        return ["Пока нет отзывов."]

    lines: list[str] = []
    for item in published_reviews:
        stars = "⭐" * int(item.get("rating", 0))
        lines.append(
            "\n".join(
                [
                    f"• <b>{item['author_name']}</b> {stars}",
                    f"Результат: {item.get('result', '—')}",
                    str(item["text"]),
                ]
            )
        )
    return lines


def build_contacts_text() -> str:
    contacts = trainer_profile.get("contacts", {})
    return (
        "📞 <b>Контакты</b>\n\n"
        f"Telegram: {contacts.get('telegram', '—')}\n"
        f"Ссылка: {contacts.get('cta_url', '—')}"
    )


def _build_about_text() -> str:
    audience_lines = "\n".join(f"• {line}" for line in trainer_profile.get("audience", []))
    uniqueness_lines = "\n".join(f"• {line}" for line in trainer_profile.get("uniqueness", []))
    services_lines = "\n\n".join(_build_services_lines())
    reviews_lines = "\n\n".join(_build_reviews_lines())

    blocks = [
        "👩‍🏫 <b>Обо мне</b>",
        f"<b>Имя:</b> {trainer_profile.get('name', '—')}",
        f"<b>Позиционирование:</b> {trainer_profile.get('positioning', '—')}",
        f"<b>Аудитория:</b>\n{audience_lines or '• —'}",
        f"<b>Уникальность:</b>\n{uniqueness_lines or '• —'}",
        f"🛍 <b>Услуги</b>\n{services_lines}",
        f"💬 <b>Отзывы</b>\n{reviews_lines}",
        build_contacts_text(),
    ]
    return "\n\n".join(blocks)


async def _send_about_profile(message: Message) -> None:
    about_text = _build_about_text()
    if ABOUT_PHOTO_PATH.exists() and ABOUT_PHOTO_PATH.is_file():
        if len(about_text) <= TELEGRAM_CAPTION_LIMIT:
            await message.answer_photo(
                photo=FSInputFile(ABOUT_PHOTO_PATH),
                caption=about_text,
                reply_markup=get_contact_trainer_keyboard(),
                parse_mode="HTML",
            )
            return

        await message.answer_photo(photo=FSInputFile(ABOUT_PHOTO_PATH))
        await message.answer(
            about_text,
            reply_markup=get_contact_trainer_keyboard(),
            parse_mode="HTML",
        )
        return

    await message.answer(
        about_text,
        reply_markup=get_contact_trainer_keyboard(),
        parse_mode="HTML",
    )


async def show_about_menu_message(message: Message) -> None:
    """Show full about profile from reply keyboard command."""
    await _send_about_profile(message)


@router.callback_query(F.data == "about:menu")
async def show_about_menu(callback: CallbackQuery) -> None:
    """Show full about profile for backward compatibility with old callbacks."""
    if not callback.message:
        await callback.answer()
        return

    await _send_about_profile(callback.message)
    await callback.answer()


@router.callback_query(F.data == "about:profile")
async def show_profile(callback: CallbackQuery) -> None:
    """Show trainer profile screen."""
    if not callback.message:
        await callback.answer()
        return

    await _send_about_profile(callback.message)
    await callback.answer()


@router.callback_query(F.data == "about:services")
async def show_services(callback: CallbackQuery) -> None:
    """Show only active services."""
    if not callback.message:
        await callback.answer()
        return

    text = "🛍 <b>Услуги</b>\n\n" + "\n\n".join(_build_services_lines())
    await callback.message.edit_text(
        text,
        reply_markup=get_contact_trainer_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "about:reviews")
async def show_reviews(callback: CallbackQuery) -> None:
    """Show review list screen."""
    if not callback.message:
        await callback.answer()
        return

    text = "💬 <b>Отзывы</b>\n\n" + "\n\n".join(_build_reviews_lines())
    await callback.message.edit_text(
        text,
        reply_markup=get_contact_trainer_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "about:contacts")
async def show_contacts(callback: CallbackQuery) -> None:
    """Show contacts screen."""
    if not callback.message:
        await callback.answer()
        return

    await callback.message.edit_text(
        build_contacts_text(),
        reply_markup=get_contact_trainer_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "donate:start")
async def start_donation_flow(callback: CallbackQuery, state: FSMContext) -> None:
    """Enter donation FSM by requesting amount."""
    if not callback.message:
        await callback.answer()
        return

    await state.set_state(DonateStates.waiting_for_amount)
    await callback.message.answer(
        f"Введите сумму доната в рублях (минимум {DONATION_MIN_AMOUNT})."
    )
    await callback.answer()


@router.message(DonateStates.waiting_for_amount)
async def process_donation_amount(message: Message, state: FSMContext) -> None:
    """Validate donation amount and send user to payment."""
    raw_value = (message.text or "").strip()

    if not raw_value.isdigit():
        await message.answer("Пожалуйста, введите сумму числом, например: 500")
        return

    amount = int(raw_value)
    if amount < DONATION_MIN_AMOUNT:
        await message.answer(
            f"Минимальная сумма доната — {DONATION_MIN_AMOUNT} ₽. Попробуйте ещё раз."
        )
        return

    await state.clear()
    await create_invoice(message=message, amount_rub=amount)


@router.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery) -> None:
    """Approve pre-checkout query from Telegram."""
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message) -> None:
    """Persist successful payment and send admin event."""
    if not message.successful_payment or not message.from_user:
        return

    payload = message.successful_payment.invoice_payload
    if not payload.startswith("donation:"):
        return

    _, payment_ref = payload.split(":", 1)
    amount_rub = message.successful_payment.total_amount // 100
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
        currency=message.successful_payment.currency,
        status="successful",
        provider_payment_id=message.successful_payment.telegram_payment_charge_id,
        payload={
            "invoice_payload": payload,
            "payment_ref": payment_ref,
            "telegram_payment_charge_id": message.successful_payment.telegram_payment_charge_id,
            "provider_payment_charge_id": message.successful_payment.provider_payment_charge_id,
            "purpose": "donation",
        },
    )
    try:
        await send_payment_event(
            bot=message.bot,
            user_id=user_id,
            payment_id=payment_id,
            amount_rub=amount_rub,
            purpose="donation",
        )
    except Exception:
        logger.exception("Failed to notify admin about payment user_id=%s payment_id=%s", user_id, payment_id)

    await message.answer("Спасибо за оплату! Платёж успешно получен.")
