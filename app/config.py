"""Application configuration."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError, field_validator


class Settings(BaseModel):
    """Environment-backed application settings."""

    telegram_bot_token: str
    provider_token: str
    shop_id: str
    secret_key: str
    admin_id: int = 5948629306
    database_path: str = "fitness.db"

    @field_validator("telegram_bot_token", "provider_token", "shop_id", "secret_key")
    @classmethod
    def validate_required_string(cls, value: str) -> str:
        """Ensure required settings are not empty or whitespace only."""
        if not value or not value.strip():
            raise ValueError("must not be empty")
        return value


def _read_env() -> dict[str, Any]:
    """Read settings from environment variables."""
    return {
        "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
        "provider_token": os.getenv("PROVIDER_TOKEN", ""),
        "shop_id": os.getenv("SHOP_ID", ""),
        "secret_key": os.getenv("SECRET_KEY", ""),
        "admin_id": os.getenv("ADMIN_ID", 5948629306),
        "database_path": os.getenv("DATABASE_PATH", "fitness.db"),
    }


def load_settings() -> Settings:
    """Load and validate settings from environment variables."""
    load_dotenv()
    raw_data = _read_env()

    try:
        return Settings.model_validate(raw_data)
    except ValidationError as exc:
        missing_or_invalid: list[str] = []
        field_to_env_name = {
            "telegram_bot_token": "TELEGRAM_BOT_TOKEN",
            "provider_token": "PROVIDER_TOKEN",
            "shop_id": "SHOP_ID",
            "secret_key": "SECRET_KEY",
            "admin_id": "ADMIN_ID",
            "database_path": "DATABASE_PATH",
        }

        for err in exc.errors():
            field_name = err.get("loc", [""])[0]
            env_name = field_to_env_name.get(str(field_name), str(field_name))
            missing_or_invalid.append(env_name)

        joined = ", ".join(sorted(set(missing_or_invalid)))
        raise RuntimeError(
            "Invalid configuration. Please set the following env vars correctly: "
            f"{joined}."
        ) from exc
