from __future__ import annotations

import argparse
import logging
import sys
import time
from typing import Any

import httpx

from config import BotConfig, get_config
from handlers import CommandContext, route_text
from services import LLMClient, LMSClient


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def build_context(config: BotConfig) -> CommandContext:
    return CommandContext(
        config=config,
        lms_client=LMSClient(
            base_url=config.lms_api_base_url,
            api_key=config.lms_api_key,
        ),
        llm_client=LLMClient(
            model=config.llm_api_model,
            api_key=config.llm_api_key,
            base_url=config.llm_api_base_url,
        ),
    )


def run_test_mode(raw_input: str) -> int:
    config = get_config(require_bot_token=False)
    context = build_context(config)
    response = route_text(context, raw_input)
    print(response)
    return 0


def telegram_api_request(
    config: BotConfig,
    method: str,
    payload: dict[str, Any],
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    url = f"{config.telegram_api_base}/{method}"
    timeout = httpx.Timeout(timeout_seconds, connect=10.0)

    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, json=payload)

    response.raise_for_status()
    data = response.json()

    if not isinstance(data, dict):
        raise RuntimeError(f"Telegram API returned unexpected payload: {data!r}")

    if not data.get("ok", False):
        raise RuntimeError(f"Telegram API error: {data!r}")

    return data


def get_updates(config: BotConfig, offset: int | None) -> list[dict[str, Any]]:
    payload: dict[str, Any] = {
        "timeout": 60,
        "allowed_updates": ["message"],
    }
    if offset is not None:
        payload["offset"] = offset

    data = telegram_api_request(
        config,
        "getUpdates",
        payload,
        timeout_seconds=70.0,
    )
    result = data.get("result", [])

    if not isinstance(result, list):
        return []

    safe_result: list[dict[str, Any]] = []
    for item in result:
        if isinstance(item, dict):
            safe_result.append(item)
    return safe_result


def send_message(config: BotConfig, chat_id: int, text: str) -> None:
    telegram_api_request(
        config,
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        },
        timeout_seconds=15.0,
    )


def handle_update(
    config: BotConfig,
    context: CommandContext,
    update: dict[str, Any],
) -> None:
    message = update.get("message")
    if not isinstance(message, dict):
        return

    text = message.get("text")
    chat = message.get("chat")

    if not isinstance(text, str):
        return
    if not isinstance(chat, dict):
        return

    chat_id = chat.get("id")
    if not isinstance(chat_id, int):
        return

    response_text = route_text(context, text)
    send_message(config, chat_id, response_text)


def run_telegram_mode() -> int:
    config = get_config(require_bot_token=True)
    context = build_context(config)

    logging.info("Bot started in Telegram mode")
    offset: int | None = None

    try:
        while True:
            try:
                updates = get_updates(config, offset)

                for update in updates:
                    update_id = update.get("update_id")
                    if isinstance(update_id, int):
                        offset = update_id + 1

                    handle_update(config, context, update)

            except httpx.HTTPError:
                logging.exception("HTTP error while polling Telegram")
                time.sleep(3)
            except Exception:
                logging.exception("Unexpected error while polling Telegram")
                time.sleep(3)
    except KeyboardInterrupt:
        logging.info("Bot stopped")
        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SE Toolkit Lab 7 bot scaffold",
    )
    parser.add_argument(
        "--test",
        nargs="?",
        const="/start",
        metavar="TEXT",
        help='Run bot in local test mode, e.g. --test "/start"',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        if args.test is not None:
            return run_test_mode(args.test)
        return run_telegram_mode()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
