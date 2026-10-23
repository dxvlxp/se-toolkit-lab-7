"""Run the LMS bot using Telegram long polling or a Telegram-free CLI."""

import argparse
import logging
import sys
import time
from typing import Any, cast

import httpx

from config import BotConfig, get_config
from handlers import CommandContext, route_text
from services.llm_client import LLMClient
from services.lms_client import LMSClient


logger = logging.getLogger(__name__)
KEYBOARD = {
    "inline_keyboard": [
        [
            {"text": "Health", "callback_data": "/health"},
            {"text": "Labs", "callback_data": "/labs"},
            {"text": "Help", "callback_data": "/help"},
        ]
    ]
}


class TelegramError(Exception):
    """A Telegram failure that excludes the token-bearing request URL."""


def build_context(config: BotConfig) -> CommandContext:
    return CommandContext(
        lms=LMSClient(config.lms_api_base_url, config.lms_api_key),
        llm=LLMClient(
            config.llm_api_base_url, config.llm_api_key, config.llm_api_model
        ),
    )


def telegram_call(config: BotConfig, method: str, payload: dict[str, Any]) -> Any:
    try:
        with httpx.Client(timeout=httpx.Timeout(45, connect=10)) as client:
            response = client.post(
                f"https://api.telegram.org/bot{config.bot_token}/{method}", json=payload
            )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise TelegramError("Telegram returned an invalid response")
        data = cast(dict[str, Any], data)
        if not data.get("ok"):
            raise TelegramError("Telegram rejected the request")
        return data.get("result")
    except httpx.HTTPStatusError as exc:
        raise TelegramError(f"Telegram HTTP {exc.response.status_code}") from None
    except httpx.RequestError:
        raise TelegramError(
            "Telegram network request failed; check connectivity"
        ) from None
    except ValueError:
        raise TelegramError("Telegram returned invalid JSON") from None


def send_reply(config: BotConfig, chat_id: int, text: str) -> None:
    # A conservative UTF-16 budget keeps emoji-heavy messages within Telegram limits.
    chunks: list[str] = []
    current: list[str] = []
    units = 0
    for character in text:
        width = 2 if ord(character) > 0xFFFF else 1
        if units + width > 3500:
            chunks.append("".join(current))
            current, units = [], 0
        current.append(character)
        units += width
    if current:
        chunks.append("".join(current))
    for index, chunk in enumerate(chunks):
        payload: dict[str, Any] = {"chat_id": chat_id, "text": chunk}
        if index == len(chunks) - 1:
            payload["reply_markup"] = KEYBOARD
        telegram_call(config, "sendMessage", payload)


def handle_update(
    config: BotConfig, context: CommandContext, update: dict[str, Any]
) -> None:
    callback = update.get("callback_query")
    if isinstance(callback, dict):
        callback = cast(dict[str, Any], callback)
        if not isinstance(callback.get("id"), str):
            return
        telegram_call(
            config, "answerCallbackQuery", {"callback_query_id": callback["id"]}
        )
        message = callback.get("message", {})
        text = callback.get("data", "")
        if not isinstance(text, str) or text not in {"/health", "/labs", "/help"}:
            return
    else:
        message = update.get("message", {})
        text = (
            cast(dict[str, Any], message).get("text", "")
            if isinstance(message, dict)
            else ""
        )
    if not isinstance(message, dict) or not isinstance(text, str) or not text:
        return
    chat = cast(dict[str, Any], message).get("chat", {})
    chat_id = cast(dict[str, Any], chat).get("id") if isinstance(chat, dict) else None
    if isinstance(chat_id, int):
        send_reply(config, chat_id, route_text(context, text))


def run_telegram(config: BotConfig, context: CommandContext) -> None:
    telegram_call(config, "getMe", {})
    logger.info("Application started")
    offset = 0
    while True:
        try:
            updates = telegram_call(
                config,
                "getUpdates",
                {
                    "timeout": 30,
                    "offset": offset,
                    "allowed_updates": ["message", "callback_query"],
                },
            )
            if not isinstance(updates, list):
                raise TelegramError("Telegram returned an invalid updates list")
            for update in cast(list[Any], updates):
                if not isinstance(update, dict):
                    continue
                update = cast(dict[str, Any], update)
                update_id = update.get("update_id")
                if not isinstance(update_id, int):
                    continue
                # Advance after handling. A transient failure is retried on the next poll.
                handle_update(config, context, update)
                offset = update_id + 1
        except TelegramError as exc:
            logger.warning("%s", exc)
            time.sleep(3)


def main() -> int:
    parser = argparse.ArgumentParser(description="LMS Telegram bot")
    parser.add_argument(
        "--test", metavar="TEXT", help="Run one request without Telegram"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    # HTTP logs contain Telegram request URLs, so keep third-party HTTP logging quiet.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        config = get_config(require_bot_token=args.test is None)
        context = build_context(config)
        if args.test is not None:
            print(route_text(context, args.test))
        else:
            run_telegram(config, context)
        return 0
    except (ValueError, TelegramError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
