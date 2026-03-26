from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class LMSClient:
    base_url: str
    api_key: str

    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def status_message(self) -> str:
        if self.is_configured():
            return (
                f"LMS API is configured ({self.base_url}). "
                "Real backend requests will be added in Task 2."
            )
        return (
            "LMS API is not configured yet. "
            "Fill LMS_API_BASE_URL and LMS_API_KEY in .env.bot.secret."
        )
