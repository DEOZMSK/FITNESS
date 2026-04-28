"""Start command and global menu handlers."""

from __future__ import annotations

from pathlib import Path

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message

from app.bot.handlers.about import build_contacts_text, show_about_menu_message
from app.bot.keyboards import (
    BUTTON_ABOUT,
    BUTTON_CANCEL,
    BUTTON_CONTACT,
    BUTTON_HOME_MENU,
    BUTTON_UPDATE_BOT,
    get_contact_trainer_keyboard,
    get_main_menu_keyboard,
)
from app.bot.texts import get_welcome_text
from app.bot.version import BOT_VERSION
from app.db import Database

router = Router(name=__name__)
db = Database()


def _resolve_welcome_video_path() -> Path | None:
    """Return first existing welcome video path."""
    root_dir = Path(__file__).resolve().parents[3]
    candidates = (
        Path("/data/1st.mp4"),
        root_dir / "data" / "1st.mp4",
        root_dir / "app" / "data" / "1st.mp4",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    if message.from_user:
        db.set_user_bot_version(message.from_user.id, BOT_VERSION)
    welcome_text = get_welcome_text()
    video_path = _resolve_welcome_video_path()

    if video_path:
        await message.answer_video(
            FSInputFile(video_path),
            caption=welcome_text,
            reply_markup=get_main_menu_keyboard(),
        )
        return

    await message.answer(welcome_text, reply_markup=get_main_menu_keyboard())


@router.message(F.text == BUTTON_UPDATE_BOT)
async def refresh_bot(message: Message, state: FSMContext) -> None:
    await cmd_start(message, state)


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
