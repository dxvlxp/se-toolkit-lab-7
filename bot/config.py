"""Load bot configuration without requiring Telegram for CLI checks."""

from dataclasses import dataclass
import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv


@dataclass(frozen=True)
class BotConfig:
    bot_token: str = ""
    lms_api_base_url: str = ""
    lms_api_key: str = ""
    llm_api_base_url: str = ""
    llm_api_key: str = ""
    llm_api_model: str = "coder-model"


def configured(value: str) -> bool:
    """Reject the placeholders shipped in example configuration files."""
    return bool(value and not value.startswith(("<", "YOUR_")))


def validate_url(value: str, variable: str) -> None:
    if not configured(value):
        return
    parts = urlsplit(value)
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.query
        or parts.fragment
    ):
        raise ValueError(
            f"{variable} must be an HTTP(S) URL without credentials or query"
        )


def get_config(*, require_bot_token: bool = False) -> BotConfig:
    load_dotenv(
        Path(__file__).resolve().parent.parent / ".env.bot.secret", override=False
    )
    config = BotConfig(
        bot_token=os.getenv("BOT_TOKEN", "").strip(),
        lms_api_base_url=os.getenv("LMS_API_BASE_URL", "").strip().rstrip("/"),
        lms_api_key=os.getenv("LMS_API_KEY", "").strip(),
        llm_api_base_url=os.getenv("LLM_API_BASE_URL", "").strip().rstrip("/"),
        llm_api_key=os.getenv("LLM_API_KEY", "").strip(),
        llm_api_model=os.getenv("LLM_API_MODEL", "coder-model").strip(),
    )
    validate_url(config.lms_api_base_url, "LMS_API_BASE_URL")
    validate_url(config.llm_api_base_url, "LLM_API_BASE_URL")
    if require_bot_token and not configured(config.bot_token):
        raise ValueError(
            "BOT_TOKEN is required for Telegram mode; set it in .env.bot.secret"
        )
    return config
