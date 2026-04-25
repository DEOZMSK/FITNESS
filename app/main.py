"""Entrypoint for the Telegram bot."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.bot.handlers import router as main_router
from app.config import load_settings


async def main() -> None:
    """Initialize and start bot polling."""
    logging.basicConfig(level=logging.INFO)

    settings = load_settings()

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    dp.include_router(main_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
