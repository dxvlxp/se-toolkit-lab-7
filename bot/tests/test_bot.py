"""Exercise API contracts, CLI responses, tool conversations, and Telegram actions."""

from contextlib import redirect_stdout
from importlib import import_module
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
import unittest
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

bot: Any = import_module("bot")
from config import BotConfig, get_config
from handlers import CommandContext, route_text
from services.llm_client import LLMClient
from services.lms_client import LMSClient
from services.tools import TOOLS, execute_tool


def make_context(
    api: httpx.MockTransport | None = None, llm: httpx.MockTransport | None = None
) -> CommandContext:
    return CommandContext(
        LMSClient("http://backend.test", "backend-key", transport=api),
        LLMClient("http://llm.test/v1", "llm-key", "test-model", transport=llm),
    )


class CommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.requests: list[httpx.Request] = []

        def respond(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            if request.url.path == "/items/":
                return httpx.Response(
                    200,
                    json=[
                        {"id": 1, "type": "lab", "title": "Lab 01"},
                        {"id": 2, "type": "task", "title": "Task 1"},
                        {"id": 3, "type": "lab", "title": "Lab 02"},
                    ],
                )
            return httpx.Response(
                200, json=[{"task": "Testing", "avg_score": 71.4, "attempts": 156}]
            )

        self.context = make_context(httpx.MockTransport(respond))

    def test_start_and_help_need_no_backend(self) -> None:
        self.assertIn("Welcome", route_text(self.context, "/start"))
        self.assertIn("/scores", route_text(self.context, "/help"))
        self.assertEqual(self.requests, [])

    def test_health_uses_authenticated_items_request(self) -> None:
        self.assertIn("healthy. 3 items", route_text(self.context, "/health"))
        self.assertEqual(
            self.requests[0].headers["Authorization"], "Bearer backend-key"
        )
        self.assertEqual(self.requests[0].url.path, "/items/")

    def test_labs_filter_out_tasks(self) -> None:
        reply = route_text(self.context, "/labs")
        self.assertIn("Lab 01", reply)
        self.assertIn("Lab 02", reply)
        self.assertNotIn("Task 1", reply)

    def test_scores_use_backend_fields_and_lab_parameter(self) -> None:
        reply = route_text(self.context, "/scores@my_bot\t4")
        self.assertIn("Testing: 71.4% (156 attempts)", reply)
        self.assertEqual(self.requests[0].url.params["lab"], "lab-04")

    def test_invalid_scores_arguments_do_not_call_backend(self) -> None:
        for text in (
            "/scores",
            "/scores lab-four",
            "/scores 0",
            "/scores lab-04 extra",
        ):
            with self.subTest(text=text):
                self.assertIn("Usage", route_text(self.context, text))
        self.assertEqual(self.requests, [])

    def test_unknown_and_empty_input_are_helpful(self) -> None:
        self.assertIn("/help", route_text(self.context, "/unknown"))
        self.assertIn("/help", route_text(self.context, "  "))

    def test_missing_config_is_readable(self) -> None:
        self.context.lms = LMSClient("", "")
        self.assertIn("LMS_API_KEY", route_text(self.context, "/health"))

    def test_backend_http_errors_include_status(self) -> None:
        for status in (401, 404, 422, 502):
            self.context.lms.transport = httpx.MockTransport(
                lambda _: httpx.Response(status)
            )
            self.assertIn(f"HTTP {status}", route_text(self.context, "/health"))

    def test_backend_connection_failure_preserves_reason(self) -> None:
        def fail(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused", request=request)

        self.context.lms.transport = httpx.MockTransport(fail)
        reply = route_text(self.context, "/health")
        self.assertIn("connection refused", reply)
        self.assertNotIn("Traceback", reply)

    def test_backend_timeout(self) -> None:
        def fail(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timeout", request=request)

        self.context.lms.transport = httpx.MockTransport(fail)
        self.assertIn("timed out", route_text(self.context, "/health"))

    def test_empty_data(self) -> None:
        self.context.lms.transport = httpx.MockTransport(
            lambda _: httpx.Response(200, json=[])
        )
        self.assertIn("No labs", route_text(self.context, "/labs"))
        self.assertIn("No scores", route_text(self.context, "/scores lab-99"))

    def test_invalid_backend_payloads(self) -> None:
        for payload in ({"wrong": "shape"}, [5], [{"task": "Missing scores"}]):
            self.context.lms.transport = httpx.MockTransport(
                lambda _: httpx.Response(200, json=payload)
            )
            self.assertIn("Backend error", route_text(self.context, "/scores lab-04"))

    def test_invalid_json(self) -> None:
        self.context.lms.transport = httpx.MockTransport(
            lambda _: httpx.Response(200, text="not json")
        )
        self.assertIn("Invalid JSON", route_text(self.context, "/health"))


def tool_call(
    name: str, arguments: str = "{}", call_id: str = "call-1"
) -> dict[str, Any]:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": arguments},
    }


class ToolTests(unittest.TestCase):
    def test_all_nine_tools_match_endpoints_and_auth(self) -> None:
        requests: list[httpx.Request] = []

        def respond(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(
                200,
                json={}
                if request.url.path in {"/pipeline/sync", "/analytics/completion-rate"}
                else [],
            )

        client = make_context(httpx.MockTransport(respond)).lms
        names = [schema["function"]["name"] for schema in TOOLS]
        self.assertEqual(len(set(names)), 9)
        for name in names:
            args = (
                {}
                if name in {"get_items", "get_learners", "trigger_sync"}
                else {"lab": "lab-04"}
            )
            execute_tool(client, name, args)
        self.assertEqual(
            [request.url.path for request in requests],
            [
                "/items/",
                "/learners/",
                "/analytics/scores",
                "/analytics/pass-rates",
                "/analytics/timeline",
                "/analytics/groups",
                "/analytics/top-learners",
                "/analytics/completion-rate",
                "/pipeline/sync",
            ],
        )
        self.assertEqual(requests[-1].method, "POST")
        self.assertEqual(json.loads(requests[-1].content), {})
        self.assertTrue(
            all(r.headers["Authorization"] == "Bearer backend-key" for r in requests)
        )

    def test_invalid_tool_arguments_are_rejected(self) -> None:
        client = make_context().lms
        for name, args in (
            ("delete_everything", {}),
            ("get_items", {"path": "/private"}),
            ("get_scores", {}),
            ("get_scores", {"lab": 4}),
            ("get_top_learners", {"lab": "lab-04", "limit": True}),
            ("get_top_learners", {"lab": "lab-04", "limit": 100}),
        ):
            with self.subTest(name=name, args=args), self.assertRaises(ValueError):
                execute_tool(client, name, args)

    def test_model_can_chain_multiple_backend_calls(self) -> None:
        conversations: list[dict[str, Any]] = []
        backend_paths: list[str] = []

        def backend(request: httpx.Request) -> httpx.Response:
            backend_paths.append(str(request.url))
            if request.url.path == "/items/":
                return httpx.Response(
                    200,
                    json=[
                        {"type": "lab", "title": "Lab 01"},
                        {"type": "lab", "title": "Lab 02"},
                    ],
                )
            score = 50 if request.url.params["lab"] == "lab-01" else 90
            return httpx.Response(
                200, json=[{"task": "Task", "avg_score": score, "attempts": 10}]
            )

        def model(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            conversations.append(body)
            self.assertEqual(request.url.path, "/v1/chat/completions")
            self.assertEqual(request.headers["Authorization"], "Bearer llm-key")
            round_number = len(conversations)
            if round_number == 1:
                message = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tool_call("get_items")],
                }
            elif round_number == 2:
                self.assertEqual(body["messages"][-1]["role"], "tool")
                message = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        tool_call("get_pass_rates", '{"lab":"lab-01"}', "rates-1"),
                        tool_call("get_pass_rates", '{"lab":"lab-02"}', "rates-2"),
                    ],
                }
            else:
                tool_results = [m for m in body["messages"] if m["role"] == "tool"]
                self.assertEqual(len(tool_results), 3)
                self.assertEqual(tool_results[-1]["tool_call_id"], "rates-2")
                self.assertIn('"avg_score": 90', tool_results[-1]["content"])
                message = {
                    "role": "assistant",
                    "content": "Lab 01 has the lowest average score: 50%.",
                }
            return httpx.Response(200, json={"choices": [{"message": message}]})

        context = make_context(httpx.MockTransport(backend), httpx.MockTransport(model))
        output = StringIO()
        with redirect_stdout(output):
            reply = route_text(context, "Which lab has the lowest average score?")
        self.assertIn("Lab 01", reply)
        self.assertEqual(len(backend_paths), 3)
        self.assertEqual(output.getvalue(), "")

    def test_backend_error_survives_model_summary(self) -> None:
        counter = 0

        def model(_: httpx.Request) -> httpx.Response:
            nonlocal counter
            counter += 1
            message = (
                {"tool_calls": [tool_call("get_items")]}
                if counter == 1
                else {"content": "Cannot fetch data."}
            )
            return httpx.Response(200, json={"choices": [{"message": message}]})

        context = make_context(
            httpx.MockTransport(lambda _: httpx.Response(502)),
            httpx.MockTransport(model),
        )
        self.assertIn("HTTP 502", route_text(context, "List labs"))

    def test_bad_arguments_are_returned_to_model(self) -> None:
        counter = 0

        def model(request: httpx.Request) -> httpx.Response:
            nonlocal counter
            counter += 1
            if counter == 1:
                message = {"tool_calls": [tool_call("get_pass_rates", "not-json")]}
            else:
                messages = json.loads(request.content)["messages"]
                self.assertIn("error", json.loads(messages[-1]["content"]))
                message = {"content": "Please specify a lab."}
            return httpx.Response(200, json={"choices": [{"message": message}]})

        context = make_context(llm=httpx.MockTransport(model))
        self.assertIn("specify", route_text(context, "scores"))

    def test_model_failure_is_readable(self) -> None:
        context = make_context(llm=httpx.MockTransport(lambda _: httpx.Response(401)))
        self.assertIn("HTTP 401", route_text(context, "hello"))

    def test_invalid_model_responses_are_readable(self) -> None:
        payloads: list[dict[str, Any]] = [
            {},
            {"choices": []},
            {"choices": [{"message": {"content": ""}}]},
        ]
        for payload in payloads:
            context = make_context(
                llm=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
            )
            self.assertIn("LLM error", route_text(context, "hello"))

    def test_loop_limit(self) -> None:
        transport = httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={
                    "choices": [{"message": {"tool_calls": [tool_call("get_items")]}}]
                },
            )
        )
        context = make_context(
            httpx.MockTransport(lambda _: httpx.Response(200, json=[])), transport
        )
        context.llm.max_rounds = 2
        self.assertIn("limit reached", route_text(context, "Compare labs"))


class TransportTests(unittest.TestCase):
    def test_cli_start_needs_no_telegram_token(self) -> None:
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("BOT_", "LMS_", "LLM_"))
        }
        result = subprocess.run(
            [sys.executable, str(Path(bot.__file__)), "--test", "/start"],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Welcome", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_callback_acknowledged_and_dispatched(self) -> None:
        with (
            patch.object(bot, "telegram_call") as call,
            patch.object(bot, "send_reply") as reply,
        ):
            bot.handle_update(
                BotConfig(bot_token="token"),
                make_context(),
                {
                    "callback_query": {
                        "id": "cb-1",
                        "data": "/help",
                        "message": {"chat": {"id": 42}},
                    },
                },
            )
            self.assertEqual(call.call_args.args[1], "answerCallbackQuery")
            self.assertIn("/scores", reply.call_args.args[2])

    def test_long_messages_are_split_without_losing_text(self) -> None:
        text = "😀" * 5000
        with patch.object(bot, "telegram_call") as call:
            bot.send_reply(BotConfig(), 42, text)
            chunks = [args.args[2]["text"] for args in call.call_args_list]
            self.assertEqual("".join(chunks), text)
            self.assertTrue(
                all(len(chunk.encode("utf-16-le")) // 2 <= 3500 for chunk in chunks)
            )

    def test_config_prefers_environment_over_file(self) -> None:
        with (
            patch.dict(os.environ, {"LMS_API_KEY": "environment-value"}),
            patch("config.load_dotenv"),
        ):
            self.assertEqual(get_config().lms_api_key, "environment-value")

    def test_token_required_only_for_telegram(self) -> None:
        with patch.dict(os.environ, {"BOT_TOKEN": ""}), patch("config.load_dotenv"):
            with self.assertRaises(ValueError):
                get_config(require_bot_token=True)


if __name__ == "__main__":
    unittest.main()
