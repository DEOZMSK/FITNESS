"""About router screens and donation FSM flow."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
)

from app.config import load_settings
from app.data.products import products
from app.data.reviews import reviews
from app.data.trainer_profile import trainer_profile
from app.bot.states import DonateStates

router = Router(name=__name__)

DONATION_MIN_AMOUNT = 300


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


def _diagnostics_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💖 Поддержать донатом", callback_data="donate:start")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="start:menu")],
        ]
    )


def _about_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="about:menu")]]
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
                f"\n• <b>{item['title']}</b>\n"
                f"{item['description']}\n"
                f"Стоимость: {item['price']} {item['currency']}"
            )
        text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=_about_back_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "about:reviews")
async def show_reviews(callback: CallbackQuery) -> None:
    """Show review list screen."""
    if not callback.message:
        await callback.answer()
        return

    if not reviews:
        text = "Пока нет отзывов."
    else:
        lines = ["💬 <b>Отзывы</b>"]
        for item in reviews:
            stars = "⭐" * int(item.get("rating", 0))
            lines.append(f"\n• <b>{item['author']}</b> {stars}\n{item['text']}")
        text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=_about_back_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "about:contacts")
async def show_contacts(callback: CallbackQuery) -> None:
    """Show contacts screen."""
    if not callback.message:
        await callback.answer()
        return

    text = (
        "📞 <b>Контакты</b>\n\n"
        f"{trainer_profile['contacts']}\n\n"
        "🌐 <b>Соцсети</b>\n"
        f"{trainer_profile['social']}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=_about_back_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "diag:start")
async def show_diagnostics_intro(callback: CallbackQuery) -> None:
    """Show diagnostics intro and donation entry point."""
    if not callback.message:
        await callback.answer()
        return

    await callback.message.edit_text(
        "🧪 Фитнес-диагностика\n\n"
        "Это стартовый этап для оценки текущего состояния и целей.\n"
        "Если хотите поддержать проект, можно отправить донат.",
        reply_markup=_diagnostics_keyboard(),
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

    settings = load_settings()
    await state.clear()

    await message.bot.send_invoice(
        chat_id=message.chat.id,
        title="Донат тренеру",
        description="Поддержка фитнес-проекта",
        payload=f"donation:{message.from_user.id if message.from_user else 'unknown'}",
        provider_token=settings.provider_token,
        currency="RUB",
        prices=[LabeledPrice(label="Донат", amount=amount * 100)],
        start_parameter="fitness-donation",
    )
