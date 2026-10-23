"""Describe and validate the nine LMS tools exposed to the language model."""

import re
from typing import Any

from .lms_client import LMSClient


DESCRIPTIONS = {
    "get_items": "List all course items. Filter type=lab to discover labs and their titles before comparing labs.",
    "get_learners": "List enrolled learners and their student groups.",
    "get_scores": "Get four score-distribution buckets and counts for one lab, not per-task averages.",
    "get_pass_rates": "Get per-task average scores (avg_score, percent) and attempt counts for one lab. Use for task scores and comparing labs; this is an average, not the proportion of students who passed.",
    "get_timeline": "Get daily submission counts for one lab, ordered by date.",
    "get_groups": "Get average scores and distinct student counts by group for one lab. Use to compare or rank groups.",
    "get_top_learners": "Get the top learners ranked by average score within a required lab. Ask which lab if unspecified.",
    "get_completion_rate": "Get the percentage of active learners who achieved at least 60 for one lab, plus passed and total counts.",
    "trigger_sync": "Refresh LMS data from the autochecker. This changes backend data; call only when the user explicitly asks to sync or refresh the data. Never call merely to answer a question.",
}


def tool_schema(name: str, description: str) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []
    if name not in {"get_items", "get_learners", "trigger_sync"}:
        properties["lab"] = {
            "type": "string",
            "description": "Lab identifier in lab-NN format, e.g. lab-04. Extract the number from the lab title returned by get_items.",
        }
        required.append("lab")
    if name == "get_top_learners":
        properties["limit"] = {"type": "integer", "minimum": 1, "maximum": 50}
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }


TOOLS = [tool_schema(name, description) for name, description in DESCRIPTIONS.items()]


def execute_tool(client: LMSClient, name: str, arguments: dict[str, Any]) -> Any:
    """Allow only registered tools with the documented arguments."""
    if name not in DESCRIPTIONS:
        raise ValueError(f"Unknown tool: {name}")
    no_arguments = {"get_items", "get_learners", "trigger_sync"}
    allowed: set[str] = set() if name in no_arguments else {"lab"}
    if name == "get_top_learners":
        allowed.add("limit")
    if set(arguments) - allowed:
        raise ValueError("Unexpected tool arguments")
    if name not in no_arguments:
        lab = arguments.get("lab")
        if not isinstance(lab, str) or not re.fullmatch(r"lab-\d{2,3}", lab):
            raise ValueError("lab must be a lab-NN identifier, e.g. lab-04")
    if name == "get_top_learners":
        limit = arguments.get("limit", 5)
        if type(limit) is not int or not 1 <= limit <= 50:
            raise ValueError("limit must be an integer between 1 and 50")
    # This dispatch executes the model's chosen tool; it never inspects user text.
    if name == "get_items":
        return client.get_items()
    if name == "get_learners":
        return client.get_learners()
    if name == "trigger_sync":
        return client.trigger_sync()
    lab = arguments["lab"]
    if name == "get_scores":
        return client.get_scores(lab)
    if name == "get_pass_rates":
        return client.get_pass_rates(lab)
    if name == "get_timeline":
        return client.get_timeline(lab)
    if name == "get_groups":
        return client.get_groups(lab)
    if name == "get_completion_rate":
        return client.get_completion_rate(lab)
    return client.get_top_learners(lab, arguments.get("limit", 5))
