"""Route commands through the same functions in CLI and Telegram mode."""

from dataclasses import dataclass
import re

from services.lms_client import BackendError, LMSClient
from services.llm_client import LLMClient, LLMError


HELP = (
    "/start — welcome and quick actions\n"
    "/help — show available commands\n"
    "/health — check the LMS backend\n"
    "/labs — list available labs\n"
    "/scores <lab> — task averages and attempt counts, e.g. /scores lab-04\n\n"
    "You can also ask questions in plain language, e.g. "
    "'Which lab has the lowest average score?'"
)


@dataclass
class CommandContext:
    lms: LMSClient
    llm: LLMClient


def normalize_lab(argument: str) -> str | None:
    """Normalize slash-command arguments; natural-language routing uses the LLM."""
    match = re.fullmatch(r"(?:lab[- ]?)?(\d{1,3})", argument.strip(), re.IGNORECASE)
    if not match or int(match.group(1)) < 1:
        return None
    return f"lab-{int(match.group(1)):02d}"


def handle_health(context: CommandContext) -> str:
    items = context.lms.get_items()
    return f"Backend is healthy. {len(items)} items available."


def handle_labs(context: CommandContext) -> str:
    labs = [row for row in context.lms.get_items() if row.get("type") == "lab"]
    if not labs:
        return "No labs available. Populate the backend with the ETL sync first."
    return "Available labs:\n" + "\n".join(
        f"- {row.get('title', 'Untitled lab')}" for row in labs
    )


def handle_scores(context: CommandContext, argument: str) -> str:
    lab = normalize_lab(argument)
    if lab is None:
        return "Usage: /scores lab-04 (a lab identifier is required)."
    rows = context.lms.get_pass_rates(lab)
    if not rows:
        return f"No scores found for {lab}. Check the lab identifier and synced data."
    lines = [f"Task averages for {lab}:"]
    for row in rows:
        try:
            score = float(row["avg_score"])
            attempts = int(row["attempts"])
            task = str(row["task"])
        except (KeyError, TypeError, ValueError) as exc:
            raise BackendError(
                "Unexpected score response: missing or invalid task data"
            ) from exc
        lines.append(f"- {task}: {score:.1f}% ({attempts} attempts)")
    return "\n".join(lines)


def route_text(context: CommandContext, text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return "Send /help to see what I can do."
    try:
        if not stripped.startswith("/"):
            return context.llm.route(stripped, context.lms)
        parts = stripped.split(maxsplit=1)
        command = parts[0].split("@", maxsplit=1)[0].lower()
        argument = parts[1] if len(parts) == 2 else ""
        if command == "/start":
            return "Welcome to the LMS bot!\n\n" + HELP
        if command == "/help":
            return HELP
        if command == "/health":
            return handle_health(context)
        if command == "/labs":
            return handle_labs(context)
        if command == "/scores":
            return handle_scores(context, argument)
        return f"Unknown command: {command}. Use /help."
    except BackendError as exc:
        return f"Backend error: {exc}"
    except LLMError as exc:
        return f"LLM error: {exc}. You can still use /help and slash commands."
