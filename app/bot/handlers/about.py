"""About router screens and donation FSM flow."""

import logging
import random
from pathlib import Path
from typing import Optional

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    PreCheckoutQuery,
)

from app.bot.states import DonateStates
from app.data.products import products
from app.data.reviews import reviews
from app.data.trainer_profile import trainer_profile
from app.db import Database
from app.services import DONATION_MIN_AMOUNT, create_invoice, send_payment_event

router = Router(name=__name__)
logger = logging.getLogger(__name__)
ABOUT_PHOTO_PATH = Path("/data/me.png")


def _get_contact_url() -> str:
    contacts = trainer_profile.get("contacts", {})
    return contacts.get("cta_url") or "https://t.me/Al0PBEDA"


def get_about_section_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Услуги и цены", callback_data="about:services")],
            [InlineKeyboardButton(text="💬 Отзывы", callback_data="about:review_random")],
            [InlineKeyboardButton(text="📞 Контакты", callback_data="about:contacts")],
            [InlineKeyboardButton(text="💳 Поддержать проект", callback_data="donate:start")],
        ]
    )


def get_services_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Написать Лене", url=_get_contact_url())],
            [InlineKeyboardButton(text="💳 Поддержать проект", callback_data="donate:start")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="about:menu")],
        ]
    )


def get_review_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Ещё отзыв", callback_data="about:review_random")],
            [InlineKeyboardButton(text="📋 Услуги и цены", callback_data="about:services")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="about:menu")],
        ]
    )


def get_contacts_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Написать Лене", url=_get_contact_url())],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="about:menu")],
        ]
    )


def _build_services_text() -> str:
    active_products = [item for item in products if item.get("is_active")]
    if not active_products:
        return "📋 <b>Услуги и цены</b>\n\nСейчас активных услуг нет."

    blocks = ["📋 <b>Услуги и цены</b>"]
    for item in active_products:
        blocks.append(
            "\n".join(
                [
                    f"<b>{item['name']}</b>",
                    str(item["description"]),
                    "",
                    f"📍 <b>Формат:</b> {item.get('format', '—')}",
                    f"🎯 <b>Результат:</b> {item.get('result', '—')}",
                    f"💰 <b>Стоимость:</b> {item['price']} {item['currency']}",
                ]
            )
        )
    blocks.append(
        "<i>Если не уверены, с чего начать, лучше начать с диагностики. "
        "Она покажет, какая нагрузка и формат сейчас подходят.</i>"
    )
    return "\n\n".join(blocks)


def _build_random_review_text(review: dict) -> str:
    stars = "⭐" * int(review.get("rating", 0))
    return "\n\n".join(
        [
            "💬 <b>Отзыв клиента</b>",
            f"<b>{review.get('author_name', 'Клиент')}</b> {stars}",
            f"<b>Результат:</b> {review.get('result', '—')}",
            str(review.get("text", "")),
            "<i>Нажмите кнопку ниже, чтобы посмотреть ещё один отзыв.</i>",
        ]
    )


def _pick_random_review_index(published_reviews: list[dict], last_index: Optional[int]) -> int:
    indexes = list(range(len(published_reviews)))
    if len(indexes) > 1 and last_index in indexes:
        indexes.remove(last_index)
    return random.choice(indexes)


def build_contacts_text() -> str:
    contacts = trainer_profile.get("contacts", {})
    return (
        "📞 <b>Контакты</b>\n\n"
        f"Telegram: {contacts.get('telegram', '—')}\n"
        f"Ссылка: {contacts.get('cta_url', '—')}\n\n"
        "Если хотите начать без хаоса — напишите Лене, она подскажет первый шаг."
    )


def _build_about_text() -> str:
    audience_lines = "\n".join(f"• {line}" for line in trainer_profile.get("audience", []))
    uniqueness_lines = "\n".join(f"• {line}" for line in trainer_profile.get("uniqueness", []))

    blocks = [
        "👩‍🏫 <b>Обо мне</b>",
        f"<b>{trainer_profile.get('name', 'Елена')}</b>",
        trainer_profile.get("positioning", ""),
        f"<b>Ко мне приходят, когда:</b>\n{audience_lines or '• хочется начать без хаоса'}",
        f"<b>Мой подход:</b>\n{uniqueness_lines or '• диагностика, план и поддержка'}",
        (
            "<i>Здесь не про наказать себя тренировками. "
            "Здесь про понятный старт, спокойную систему и тело, с которым легче жить.</i>"
        ),
        "Выберите раздел ниже 👇",
    ]
    return "\n\n".join(block for block in blocks if block)


async def _safe_edit_or_answer(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup,
) -> None:
    if not callback.message:
        await callback.answer()
        return

    try:
        await callback.message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        await callback.message.answer(
            text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )

    await callback.answer()


async def _send_about_profile(message: Message) -> None:
    about_text = _build_about_text()
    if ABOUT_PHOTO_PATH.exists() and ABOUT_PHOTO_PATH.is_file():
        await message.answer_photo(photo=FSInputFile(ABOUT_PHOTO_PATH))

    await message.answer(
        about_text,
        reply_markup=get_about_section_keyboard(),
        parse_mode="HTML",
    )


async def show_about_menu_message(message: Message) -> None:
    """Show full about profile from reply keyboard command."""
    await _send_about_profile(message)


@router.callback_query(F.data == "about:menu")
async def show_about_menu(callback: CallbackQuery) -> None:
    """Show full about profile for backward compatibility with old callbacks."""
    await _safe_edit_or_answer(
        callback,
        _build_about_text(),
        get_about_section_keyboard(),
    )


@router.callback_query(F.data == "about:profile")
async def show_profile(callback: CallbackQuery) -> None:
    """Show trainer profile screen."""
    await _safe_edit_or_answer(
        callback,
        _build_about_text(),
        get_about_section_keyboard(),
    )


@router.callback_query(F.data == "about:services")
async def show_services(callback: CallbackQuery) -> None:
    """Show only active services."""
    await _safe_edit_or_answer(
        callback,
        _build_services_text(),
        get_services_keyboard(),
    )


@router.callback_query(F.data == "about:review_random")
async def show_random_review(callback: CallbackQuery, state: FSMContext) -> None:
    published_reviews = [item for item in reviews if item.get("is_published", True)]

    if not published_reviews:
        await _safe_edit_or_answer(
            callback,
            "💬 <b>Отзывы</b>\n\nПока нет опубликованных отзывов.",
            get_review_keyboard(),
        )
        return

    data = await state.get_data()
    last_index = data.get("last_review_index")
    if not isinstance(last_index, int):
        last_index = None

    current_index = _pick_random_review_index(published_reviews, last_index)
    await state.update_data(last_review_index=current_index)

    await _safe_edit_or_answer(
        callback,
        _build_random_review_text(published_reviews[current_index]),
        get_review_keyboard(),
    )


@router.callback_query(F.data == "about:reviews")
async def show_reviews(callback: CallbackQuery, state: FSMContext) -> None:
    """Backward-compatible alias to random review screen."""
    await show_random_review(callback, state)


@router.callback_query(F.data == "about:contacts")
async def show_contacts(callback: CallbackQuery) -> None:
    """Show contacts screen."""
    await _safe_edit_or_answer(
        callback,
        build_contacts_text(),
        get_contacts_keyboard(),
    )


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
