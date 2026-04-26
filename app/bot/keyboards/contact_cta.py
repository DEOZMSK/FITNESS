"""Shared CTA keyboard for contacting trainer."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

CONTACT_TRAINER_TEXT = "💬 Написать тренеру"
CONTACT_TRAINER_URL = "https://t.me/Al0PBEDA"


def get_contact_trainer_keyboard() -> InlineKeyboardMarkup:
    """Return unified CTA button to contact trainer."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=CONTACT_TRAINER_TEXT, url=CONTACT_TRAINER_URL)],
        ]
    )
