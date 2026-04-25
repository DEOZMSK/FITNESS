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

    try:
        settings = load_settings()
    except RuntimeError as exc:
        logging.error("Failed to start bot: %s", exc)
        return

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()

    dp.include_router(main_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
