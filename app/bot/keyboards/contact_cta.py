"""Shared CTA keyboard for contacting trainer."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

CONTACT_TRAINER_TEXT = "💬 Написать тренеру"
CONTACT_TRAINER_URL = "https://t.me/Al0PBEDA"
INSTAGRAM_DM_TEXT = "📩 Написать в Instagram Direct"
INSTAGRAM_DM_URL = "https://ig.me/m/soroskanele"


def get_contact_trainer_keyboard() -> InlineKeyboardMarkup:
    """Return unified CTA button to contact trainer."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=CONTACT_TRAINER_TEXT, url=CONTACT_TRAINER_URL)],
            [InlineKeyboardButton(text="💳 Поддержать проект", callback_data="donate:start")],
        ]
    )


def get_instagram_dm_keyboard() -> InlineKeyboardMarkup:
    """Return CTA button to open Instagram Direct with trainer."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=INSTAGRAM_DM_TEXT, url=INSTAGRAM_DM_URL)],
        ]
    )
