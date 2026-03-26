from __future__ import annotations

from dataclasses import dataclass

from config import BotConfig
from services.lms_client import LMSClient
from services.llm_client import LLMClient


@dataclass(slots=True)
class CommandContext:
    config: BotConfig
    lms_client: LMSClient
    llm_client: LLMClient


def handle_start(_: CommandContext) -> str:
    return (
        "Welcome to the SE Toolkit Lab 7 bot scaffold.\n"
        "The project structure is ready, test mode works, and Telegram mode is enabled.\n\n"
        "Available commands:\n"
        "/start\n"
        "/help\n"
        "/health\n"
        "/labs\n"
        "/scores <lab-id>"
    )


def handle_help(_: CommandContext) -> str:
    return (
        "Help:\n"
        "/start - show welcome message\n"
        "/help - show this help message\n"
        "/health - show scaffold health status\n"
        "/labs - placeholder for available labs\n"
        "/scores <lab-id> - placeholder for scores lookup\n\n"
        "Natural-language routing will be added in Task 3."
    )


def handle_health(context: CommandContext) -> str:
    return (
        "Bot scaffold is healthy.\n"
        "Handlers are separated from Telegram transport.\n"
        f"{context.lms_client.status_message()}"
    )


def handle_labs(_: CommandContext) -> str:
    return (
        "Labs command scaffold is ready.\n"
        "Real backend integration for available labs will be added in Task 2."
    )


def handle_scores(_: CommandContext, argument: str) -> str:
    lab_name = argument.strip() or "<missing-lab-id>"
    return (
        f"Scores command scaffold is ready for: {lab_name}\n"
        "Real score lookup will be added in Task 2."
    )


def handle_free_text(context: CommandContext, text: str) -> str:
    return (
        "Natural-language routing scaffold is ready, but the real intent router "
        "will be added in Task 3.\n"
        f"You sent: {text}\n"
        f"{context.llm_client.status_message()}"
    )


def handle_unknown_command(_: CommandContext, command: str) -> str:
    return (
        f"Unknown command: {command}\n"
        "Try /start or /help."
    )


def route_text(context: CommandContext, text: str) -> str:
    stripped = text.strip()

    if not stripped:
        return "Empty input. Try /start or /help."

    if not stripped.startswith("/"):
        return handle_free_text(context, stripped)

    first_token, _, remainder = stripped.partition(" ")
    command = first_token.split("@", maxsplit=1)[0].lower()
    argument = remainder.strip()

    if command == "/start":
        return handle_start(context)
    if command == "/help":
        return handle_help(context)
    if command == "/health":
        return handle_health(context)
    if command == "/labs":
        return handle_labs(context)
    if command == "/scores":
        return handle_scores(context, argument)

    return handle_unknown_command(context, command)
