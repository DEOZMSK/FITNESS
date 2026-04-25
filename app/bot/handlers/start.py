"""Basic start command handler."""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router(name=__name__)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Reply to /start command."""
    await message.answer("Привет! Бот запущен и готов к работе.")
