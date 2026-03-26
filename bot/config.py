from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


BOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = BOT_DIR.parent


def load_environment() -> Path | None:
    candidates = [
        Path.cwd() / ".env.bot.secret",
        BOT_DIR / ".env.bot.secret",
        REPO_ROOT / ".env.bot.secret",
        Path.cwd().parent / ".env.bot.secret",
        Path.cwd() / ".env.bot.example",
        BOT_DIR / ".env.bot.example",
        REPO_ROOT / ".env.bot.example",
        Path.cwd().parent / ".env.bot.example",
    ]

    for candidate in candidates:
        if candidate.exists():
            load_dotenv(candidate, override=False)
            return candidate
    return None


@dataclass(slots=True)
class BotConfig:
    bot_token: str
    lms_api_base_url: str
    lms_api_key: str
    llm_api_model: str
    llm_api_key: str
    llm_api_base_url: str

    @property
    def telegram_api_base(self) -> str:
        return f"https://api.telegram.org/bot{self.bot_token}"


def get_config(*, require_bot_token: bool) -> BotConfig:
    load_environment()

    config = BotConfig(
        bot_token=os.getenv("BOT_TOKEN", "").strip(),
        lms_api_base_url=os.getenv("LMS_API_BASE_URL", "").strip().rstrip("/"),
        lms_api_key=os.getenv("LMS_API_KEY", "").strip(),
        llm_api_model=os.getenv("LLM_API_MODEL", "coder-model").strip(),
        llm_api_key=os.getenv("LLM_API_KEY", "").strip(),
        llm_api_base_url=os.getenv("LLM_API_BASE_URL", "").strip().rstrip("/"),
    )

    if require_bot_token and not config.bot_token:
        raise ValueError(
            "BOT_TOKEN is required for Telegram mode. Fill it in .env.bot.secret."
        )

    return config
