"""Entrypoint for the Telegram bot."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from app.bot.handlers import router as main_router
from app.bot.middlewares import VersionGateMiddleware
from app.config import load_settings
from app.db import Database
from app.services import retry_unsent_leads


async def main() -> None:
    """Initialize and start bot polling."""
    logging.basicConfig(level=logging.INFO)

    try:
        settings = load_settings()
    except RuntimeError as exc:
        logging.error("Failed to start bot: %s", exc)
        return

    database = Database(db_path=settings.database_path)
    database.init_db()

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    await retry_unsent_leads(bot)

    dp = Dispatcher()
    version_gate = VersionGateMiddleware(database=database)
    dp.message.middleware(version_gate)
    dp.callback_query.middleware(version_gate)

    dp.include_router(main_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
