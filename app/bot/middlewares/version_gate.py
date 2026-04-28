"""Middleware that forces user refresh after bot deploy."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import BUTTON_UPDATE_BOT, get_update_bot_keyboard
from app.bot.version import BOT_VERSION
from app.db import Database

UPDATE_TEXT = (
    "🔄 Бот был обновлён.\n"
    "Чтобы всё работало корректно, нажмите кнопку ниже."
)


class VersionGateMiddleware(BaseMiddleware):
    """Guard that blocks stale clients until they confirm bot refresh."""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            return await self._handle_message(handler, event, data)
        if isinstance(event, CallbackQuery):
            return await self._handle_callback(handler, event, data)
        return await handler(event, data)

    async def _handle_message(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if event.successful_payment:
            return await handler(event, data)
        text = (event.text or "").strip()
        if text.startswith("/start") or text == BUTTON_UPDATE_BOT:
            return await handler(event, data)
        if not event.from_user:
            return await handler(event, data)
        if self._database.get_user_bot_version(event.from_user.id) == BOT_VERSION:
            return await handler(event, data)

        state = data.get("state")
        if isinstance(state, FSMContext):
            await state.clear()
        await event.answer(UPDATE_TEXT, reply_markup=get_update_bot_keyboard())
        return None

    async def _handle_callback(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        if not event.from_user:
            return await handler(event, data)
        if self._database.get_user_bot_version(event.from_user.id) == BOT_VERSION:
            return await handler(event, data)

        state = data.get("state")
        if isinstance(state, FSMContext):
            await state.clear()
        await event.answer("Бот обновлён. Нажмите «🔄 Обновить бота».", show_alert=True)
        if event.message:
            await event.message.answer(UPDATE_TEXT, reply_markup=get_update_bot_keyboard())
        return None

