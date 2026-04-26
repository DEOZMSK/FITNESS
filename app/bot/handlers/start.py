"""Start command and global menu handlers."""

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.handlers.about import build_contacts_text, show_about_menu_message
from app.bot.keyboards import (
    BUTTON_ABOUT,
    BUTTON_CANCEL,
    BUTTON_CONTACT,
    BUTTON_HOME_MENU,
    get_contact_trainer_keyboard,
    get_main_menu_keyboard,
)

router = Router(name=__name__)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Добро пожаловать! Выберите нужный раздел:", reply_markup=get_main_menu_keyboard())


@router.message(F.text == BUTTON_HOME_MENU)
async def go_home(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Возвращаю в главное меню.", reply_markup=get_main_menu_keyboard())


@router.message(F.text == BUTTON_CANCEL)
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Сценарий отменён.", reply_markup=get_main_menu_keyboard())


@router.message(F.text == BUTTON_ABOUT)
async def open_about(message: Message) -> None:
    await show_about_menu_message(message)


@router.message(F.text == BUTTON_CONTACT)
async def open_contact(message: Message) -> None:
    await message.answer(build_contacts_text(), reply_markup=get_contact_trainer_keyboard())
