"""Start command handler with main inline menu."""

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

router = Router(name=__name__)


def _start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👩‍🏫 Обо мне", callback_data="about:menu")],
            [
                InlineKeyboardButton(
                    text="🧪 Фитнес-диагностика", callback_data="diag:start"
                )
            ],
        ]
    )


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Reply to /start command."""
    await message.answer(
        "Добро пожаловать! Выберите нужный раздел:",
        reply_markup=_start_keyboard(),
    )


@router.callback_query(F.data == "start:menu")
async def back_to_start_menu(callback: CallbackQuery) -> None:
    """Return user to main menu from nested screens."""
    if not callback.message:
        await callback.answer()
        return

    await callback.message.edit_text(
        "Добро пожаловать! Выберите нужный раздел:",
        reply_markup=_start_keyboard(),
    )
    await callback.answer()
