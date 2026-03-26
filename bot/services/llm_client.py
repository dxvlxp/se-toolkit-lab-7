from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class LLMClient:
    model: str
    api_key: str
    base_url: str

    def is_configured(self) -> bool:
        return bool(self.model and self.api_key and self.base_url)

    def status_message(self) -> str:
        if self.is_configured():
            return (
                f"LLM API is configured with model '{self.model}'. "
                "Real intent routing will be added in Task 3."
            )
        return (
            "LLM API is not fully configured yet. "
            "This is okay for Task 1 scaffold verification."
        )
