"""Authenticated LMS requests with bounded timeouts and readable errors."""

from dataclasses import dataclass
from typing import Any, cast

import httpx

from config import configured


class BackendError(Exception):
    """An actionable failure that is safe to show in a bot response."""


@dataclass
class LMSClient:
    base_url: str
    api_key: str
    transport: httpx.BaseTransport | None = None

    def request(
        self, method: str, path: str, params: dict[str, str | int] | None = None
    ) -> Any:
        if not configured(self.base_url) or not configured(self.api_key):
            raise BackendError(
                "Set LMS_API_BASE_URL and LMS_API_KEY in .env.bot.secret"
            )
        try:
            with httpx.Client(
                timeout=httpx.Timeout(20, connect=5), transport=self.transport
            ) as client:
                response = client.request(
                    method,
                    f"{self.base_url.rstrip('/')}{path}",
                    params=params,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={} if method == "POST" else None,
                )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response
            raise BackendError(
                f"HTTP {status.status_code} {status.reason_phrase}. "
                "Check the backend, API key, and requested parameters."
            ) from exc
        except httpx.TimeoutException as exc:
            raise BackendError(
                f"Request timed out ({self.base_url}). Check the backend."
            ) from exc
        except httpx.RequestError as exc:
            reason = str(exc).replace(self.api_key, "[redacted]")
            raise BackendError(
                f"{type(exc).__name__}: {reason} ({self.base_url}). "
                "Check that the backend is running."
            ) from exc
        except ValueError as exc:
            raise BackendError("Invalid JSON returned by the backend") from exc

    def get_items(self) -> list[dict[str, Any]]:
        return self._rows(self.request("GET", "/items/"))

    def get_learners(self) -> list[dict[str, Any]]:
        return self._rows(self.request("GET", "/learners/"))

    def get_scores(self, lab: str) -> list[dict[str, Any]]:
        return self._rows(self.request("GET", "/analytics/scores", {"lab": lab}))

    def get_pass_rates(self, lab: str) -> list[dict[str, Any]]:
        return self._rows(self.request("GET", "/analytics/pass-rates", {"lab": lab}))

    def get_timeline(self, lab: str) -> list[dict[str, Any]]:
        return self._rows(self.request("GET", "/analytics/timeline", {"lab": lab}))

    def get_groups(self, lab: str) -> list[dict[str, Any]]:
        return self._rows(self.request("GET", "/analytics/groups", {"lab": lab}))

    def get_top_learners(self, lab: str, limit: int = 5) -> list[dict[str, Any]]:
        return self._rows(
            self.request("GET", "/analytics/top-learners", {"lab": lab, "limit": limit})
        )

    def get_completion_rate(self, lab: str) -> dict[str, Any]:
        return self._object(
            self.request("GET", "/analytics/completion-rate", {"lab": lab})
        )

    def trigger_sync(self) -> dict[str, Any]:
        return self._object(self.request("POST", "/pipeline/sync"))

    @staticmethod
    def _rows(data: Any) -> list[dict[str, Any]]:
        if not isinstance(data, list) or not all(
            isinstance(row, dict) for row in cast(list[Any], data)
        ):
            raise BackendError(
                "Unexpected backend response: expected a list of objects"
            )
        return cast(list[dict[str, Any]], data)

    @staticmethod
    def _object(data: Any) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise BackendError("Unexpected backend response: expected an object")
        return cast(dict[str, Any], data)
