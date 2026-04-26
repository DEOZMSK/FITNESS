"""Start command handler with main reply menu."""

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.about import build_contacts_text, show_about_menu_message
from app.bot.handlers.diagnostics import show_diagnostics_menu_message
from app.bot.keyboards import (
    BUTTON_ABOUT,
    BUTTON_CANCEL,
    BUTTON_CONTACT,
    BUTTON_DIAGNOSTICS,
    BUTTON_HOME_MENU,
    BUTTON_RESULTS,
    get_main_menu_keyboard,
)

router = Router(name=__name__)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Reply to /start command."""
    await message.answer(
        "Добро пожаловать! Выберите нужный раздел:",
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(F.text == BUTTON_HOME_MENU)
async def go_home_from_any_state(message: Message, state: FSMContext) -> None:
    """Global handler for returning user to the main menu."""
    await state.clear()
    await message.answer(
        "Возвращаю в главное меню.",
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(F.text == BUTTON_CANCEL)
async def cancel_from_any_state(message: Message, state: FSMContext) -> None:
    """Global handler for canceling any active flow."""
    await state.clear()
    await message.answer(
        "Сценарий отменён. Возвращаю в главное меню.",
        reply_markup=get_main_menu_keyboard(),
    )


@router.callback_query(F.data == "start:menu")
async def back_to_start_menu(callback: CallbackQuery) -> None:
    """Return user to main menu from nested screens."""
    if not callback.message:
        await callback.answer()
        return

    await callback.message.answer(
        "Добро пожаловать! Выберите нужный раздел:",
        reply_markup=get_main_menu_keyboard(),
    )
    await callback.answer()


@router.message(F.text == BUTTON_ABOUT)
async def open_about_by_text(message: Message) -> None:
    """Open about section from reply keyboard."""
    await show_about_menu_message(message)


@router.message(F.text == BUTTON_DIAGNOSTICS)
async def open_diagnostics_by_text(message: Message) -> None:
    """Open diagnostics section from reply keyboard."""
    await show_diagnostics_menu_message(message)


@router.message(F.text == BUTTON_RESULTS)
async def open_results_by_text(message: Message) -> None:
    """Open user's results section from reply keyboard."""
    await message.answer(
        "📊 Раздел «Мои результаты» пока в разработке. "
        "После прохождения диагностики результаты будут доступны здесь."
    )


@router.message(F.text == BUTTON_CONTACT)
async def open_contact_by_text(message: Message) -> None:
    """Open trainer contact section from reply keyboard."""
    await message.answer(build_contacts_text())
