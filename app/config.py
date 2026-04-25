"""Application configuration."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError


class Settings(BaseModel):
    bot_token: str



def load_settings() -> Settings:
    """Load settings from environment variables."""
    load_dotenv()
    raw_data = {
        "bot_token": os.getenv("BOT_TOKEN", ""),
    }
    try:
        return Settings.model_validate(raw_data)
    except ValidationError as exc:
        raise RuntimeError(
            "Configuration is invalid. Set BOT_TOKEN in your environment or .env file."
        ) from exc
