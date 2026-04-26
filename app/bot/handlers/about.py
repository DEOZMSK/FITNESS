"""About router screens and donation FSM flow."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    PreCheckoutQuery,
)

from app.data.products import products
from app.data.reviews import reviews
from app.data.trainer_profile import trainer_profile
from app.bot.states import DonateStates
from app.db import Database
from app.services import DONATION_MIN_AMOUNT, create_invoice, send_payment_event

router = Router(name=__name__)

def _about_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👩‍🏫 Профиль тренера", callback_data="about:profile")],
            [InlineKeyboardButton(text="🛍 Услуги", callback_data="about:services")],
            [InlineKeyboardButton(text="💬 Отзывы", callback_data="about:reviews")],
            [InlineKeyboardButton(text="📞 Контакты", callback_data="about:contacts")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="start:menu")],
        ]
    )


def _about_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="about:menu")]]
    )



def build_contacts_text() -> str:
    return (
        "📞 <b>Контакты</b>\n\n"
        f"{trainer_profile['contacts']}\n\n"
        "🌐 <b>Соцсети</b>\n"
        f"{trainer_profile['social']}"
    )


async def show_about_menu_message(message: Message) -> None:
    """Show about menu from reply keyboard command."""
    await message.answer(
        "Раздел «Обо мне». Выберите, что показать:",
        reply_markup=_about_menu_keyboard(),
    )


@router.callback_query(F.data == "about:menu")
async def show_about_menu(callback: CallbackQuery) -> None:
    """Show about menu with profile/services/reviews/contacts sections."""
    if not callback.message:
        await callback.answer()
        return

    await callback.message.edit_text(
        "Раздел «Обо мне». Выберите, что показать:",
        reply_markup=_about_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "about:profile")
async def show_profile(callback: CallbackQuery) -> None:
    """Show trainer profile screen."""
    if not callback.message:
        await callback.answer()
        return

    text = (
        f"👩‍🏫 <b>{trainer_profile['trainer_name']}</b>\n\n"
        f"{trainer_profile['bio']}\n\n"
        f"Фото: {trainer_profile['photo']}\n"
        f"CTA: {trainer_profile['cta']}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=_about_back_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "about:services")
async def show_services(callback: CallbackQuery) -> None:
    """Show only active services."""
    if not callback.message:
        await callback.answer()
        return

    active_products = [item for item in products if item.get("is_active")]

    if not active_products:
        text = "Сейчас нет активных услуг."
    else:
        lines = ["🛍 <b>Услуги</b>"]
        for item in active_products:
            lines.append(
                f"\n• <b>{item['name']}</b>\n"
                f"{item['description']}\n"
                f"Стоимость: {item['price']} {item['currency']}\n"
                f"{item.get('cta', '')}"
            )
        text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=_about_back_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "about:reviews")
async def show_reviews(callback: CallbackQuery) -> None:
    """Show review list screen."""
    if not callback.message:
        await callback.answer()
        return

    published_reviews = [item for item in reviews if item.get("is_published", True)]

    if not published_reviews:
        text = "Пока нет отзывов."
    else:
        lines = ["💬 <b>Отзывы</b>"]
        for item in published_reviews:
            stars = "⭐" * int(item.get("rating", 0))
            lines.append(f"\n• <b>{item['author_name']}</b> {stars}\n{item['text']}")
        text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=_about_back_keyboard(),
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
        reply_markup=_about_back_keyboard(),
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
        pass

    await message.answer("Спасибо за оплату! Платёж успешно получен.")
