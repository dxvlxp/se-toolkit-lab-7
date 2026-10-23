"""Bot settings. Secrets come from the environment or a local ignored .env.bot.secret."""
from dataclasses import dataclass
import os
from pathlib import Path


def _load_env_file():
    candidates = [Path.cwd() / '.env.bot.secret', Path(__file__).resolve().parent.parent / '.env.bot.secret']
    for path in candidates:
        if path.exists():
            for line in path.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    bot_token: str
    lms_url: str
    lms_key: str
    llm_url: str
    llm_key: str
    llm_model: str


def load_settings() -> Settings:
    _load_env_file()
    return Settings(
        bot_token=os.getenv('BOT_TOKEN', ''),
        lms_url=os.getenv('LMS_API_BASE_URL', 'http://localhost:42002'),
        lms_key=os.getenv('LMS_API_KEY', ''),
        llm_url=os.getenv('LLM_API_BASE_URL', 'http://localhost:42005/v1'),
        llm_key=os.getenv('LLM_API_KEY', ''),
        llm_model=os.getenv('LLM_API_MODEL', 'coder-model'),
    )
