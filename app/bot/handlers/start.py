"""Start command and global menu handlers."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command
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
from app.config import load_settings
from app.db import Database
from app.services.admin_notify import get_admin_recipients
from app.services.analytics import (
    build_daily_report_text,
    get_event_stats_for_period,
    log_event,
)

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
    user_id = None
    if message.from_user:
        db.set_user_bot_version(message.from_user.id, BOT_VERSION)
        user_id = db.upsert_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        log_event("start", telegram_id=message.from_user.id, user_id=user_id)
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
    if message.from_user:
        user_id = db.upsert_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        log_event("about_open", telegram_id=message.from_user.id, user_id=user_id)
    await show_about_menu_message(message)


@router.message(F.text == BUTTON_CONTACT)
async def open_contact(message: Message) -> None:
    if message.from_user:
        user_id = db.upsert_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        log_event("contact_open", telegram_id=message.from_user.id, user_id=user_id)
    await message.answer(build_contacts_text(), reply_markup=get_contact_trainer_keyboard())


@router.message(Command("stats_yesterday"))
async def stats_yesterday(message: Message) -> None:
    if not message.from_user:
        return
    if message.from_user.id not in get_admin_recipients():
        await message.answer("Команда доступна только администраторам.")
        return

    settings = load_settings()
    local_tz = ZoneInfo(settings.timezone)
    now_local = datetime.now(local_tz)
    report_date_local = now_local.date() - timedelta(days=1)
    start_local = datetime.combine(report_date_local, time.min, tzinfo=local_tz)
    end_local = start_local + timedelta(days=1)

    stats = get_event_stats_for_period(
        start_local.astimezone(timezone.utc),
        end_local.astimezone(timezone.utc),
    )
    text = build_daily_report_text(report_date_local, stats)
    await message.answer(text)
