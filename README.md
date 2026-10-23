# Lab 7 — Build a Client with an AI Coding Agent

[Sync your fork](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/syncing-a-fork#syncing-a-fork-branch-from-the-command-line) regularly — the lab gets updated.

## Product brief

> Build a Telegram bot that lets users interact with the LMS backend through chat. Users should be able to check system health, browse labs and scores, and ask questions in plain language. The bot should use an LLM to understand what the user wants and fetch the right data. Deploy it alongside the existing backend on the VM.

This is what a customer might tell you. Your job is to turn it into a working product using an AI coding agent (Qwen Code) as your development partner.

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  ┌──────────────┐     ┌──────────────────────────────────┐   │
│  │  Telegram    │────▶│  Your Bot                        │   │
│  │  User        │◀────│  (aiogram / python-telegram-bot) │   │
│  └──────────────┘     └──────┬───────────────────────────┘   │
│                              │                               │
│                              │ slash commands + plain text    │
│                              ├───────▶ /start, /help         │
│                              ├───────▶ /health, /labs        │
│                              ├───────▶ intent router ──▶ LLM │
│                              │                    │          │
│                              │                    ▼          │
│  ┌──────────────┐     ┌──────┴───────┐    tools/actions      │
│  │  Docker      │     │  LMS Backend │◀───── GET /items      │
│  │  Compose     │     │  (FastAPI)   │◀───── GET /analytics  │
│  │              │     │  + PostgreSQL│◀───── POST /sync      │
│  └──────────────┘     └──────────────┘                       │
└──────────────────────────────────────────────────────────────┘
```

## Requirements

### P0 — Must have

1. Testable handler architecture — handlers work without Telegram
2. CLI test mode: `cd bot && uv run bot.py --test "/command"` prints response to stdout
3. `/start` — welcome message
4. `/help` — lists all available commands
5. `/health` — calls backend, reports up/down status
6. `/labs` — lists available labs
7. `/scores <lab>` — per-task pass rates
8. Error handling — backend down produces a friendly message, not a crash

### P1 — Should have

1. Natural language intent routing — plain text interpreted by LLM
2. All 9 backend endpoints wrapped as LLM tools
3. Inline keyboard buttons for common actions
4. Multi-step reasoning (LLM chains multiple API calls)

### P2 — Nice to have

1. Rich formatting (tables, charts as images)
2. Response caching
3. Conversation context (multi-turn)

### P3 — Deployment

1. Bot containerized with Dockerfile
2. Added as service in `docker-compose.yml`
3. Deployed and running on VM
4. README documents deployment

## Learning advice

Notice the progression above: **product brief** (vague customer ask) → **prioritized requirements** (structured) → **task specifications** (precise deliverables + acceptance criteria). This is how engineering work flows.

You are not following step-by-step instructions — you are building a product with an AI coding agent. The learning comes from planning, building, testing, and debugging iteratively.

## Learning outcomes

By the end of this lab, you should be able to say:

1. I turned a vague product brief into a working Telegram bot.
2. I can ask it questions in plain language and it fetches the right data.
3. I used an AI coding agent to plan and build the whole thing.

## Tasks

### Prerequisites

1. Complete the [lab setup](./lab/setup/setup-simple.md#lab-setup)

> **Note**: First time in this course? Do the [full setup](./lab/setup/setup-full.md#lab-setup) instead.

### Required

1. [Plan and Scaffold](./lab/tasks/required/task-1.md) — P0: project structure + `--test` mode
2. [Backend Integration](./lab/tasks/required/task-2.md) — P0: slash commands + real data
3. [Intent-Based Natural Language Routing](./lab/tasks/required/task-3.md) — P1: LLM tool use
4. [Containerize and Document](./lab/tasks/required/task-4.md) — P3: containerize + deploy

### Optional

1. [Flutter Web Chatbot](./lab/tasks/optional/task-1.md)

## Bot architecture and local verification

The bot uses the Telegram Bot HTTP API for long polling. `bot/bot.py` handles
Telegram messages and inline callbacks; `bot/handlers/commands.py` contains the
same command logic used by both Telegram and CLI mode. `bot/services/` contains
the authenticated LMS client, the OpenAI-compatible LLM client, and nine tool
schemas. Natural-language requests always go to the LLM, which selects tools;
tool results are fed back into the model for its final answer.

Commands: `/start`, `/help`, `/health`, `/labs`, and `/scores lab-04`.
The scores endpoint returns task averages and attempt counts; these averages
are distinct from the percentage of learners who passed. The completion tool
reports the backend's completion percentage.

Create `.env.bot.secret` from `.env.bot.example` in the repository root.
Set `LMS_API_BASE_URL`, `LMS_API_KEY`, `LLM_API_BASE_URL`, `LLM_API_KEY`, and
`LLM_API_MODEL`. `BOT_TOKEN` is required only for Telegram mode. Environment
variables take precedence over the secret file; example files are never loaded
as credentials. Keep secrets out of Git and PR descriptions.

```sh
cd bot
uv sync --locked --no-dev
uv run --locked bot.py --test "/start"
uv run --locked bot.py --test "/health"
uv run --locked bot.py --test "/labs"
uv run --locked bot.py --test "/scores lab-04"
uv run --locked bot.py --test "which lab has the lowest average score?"
uv run --locked python -m unittest discover -s tests -v
```

The automated bot tests use controlled backend and LLM responses. They cover
request paths, Bearer authentication, formatting, invalid input, HTTP/network
failures, multi-round tool calls, callback handling, and message splitting.
They do not establish that your real services or Telegram bot are available.
Responses go to stdout in `--test` mode; tool-call diagnostics go to stderr.
Natural-language requests allow up to 12 model rounds and 64 tool calls.
If a model/service fails, the bot returns an error with a slash-command hint.

## Deploy on the VM

Complete the [lab setup](./lab/setup/setup-simple.md) first, including populating
the backend and setting up the LLM proxy. Clone this fork to
`~/se-toolkit-lab-7`, or pull the reviewed changes there. Use Python 3.14.2 and uv
for host execution. Docker installs the matching interpreter and dependencies.

Create `.env.docker.secret` from `.env.docker.example`. Fill in the backend,
database, and autochecker credentials described in setup, plus these bot values:

| Variable | Meaning |
| --- | --- |
| `BOT_TOKEN` | Telegram token from BotFather |
| `LMS_API_KEY` | Same Bearer key used by the backend |
| `LLM_API_KEY` | Key accepted by the LLM proxy/provider |
| `LLM_API_MODEL` | Model supported by that provider, e.g. `coder-model` |
| `BOT_LLM_API_BASE_URL` | Container-reachable chat API base URL, including `/v1` if required |

Compose sets the bot's LMS URL to `http://backend:8000` (or the configured
backend container port). `localhost` inside a container refers to that container.
For the host Qwen proxy, the default bot LLM URL is
`http://host.docker.internal:42005/v1`; Compose maps that hostname to the host
gateway. The proxy must listen on an interface reachable from Docker. If it is
bound only to host loopback, configure its binding/network before using this URL.
For an external provider set `BOT_LLM_API_BASE_URL` to its HTTPS API base URL.
Host CLI mode still uses `LMS_API_BASE_URL` and `LLM_API_BASE_URL` from
`.env.bot.secret`, usually `http://localhost:42002` and
`http://localhost:42005/v1` respectively.

Stop any previous host bot process before starting the container to avoid two
polling sessions for the same Telegram token. Then run from the repository root:

```sh
docker compose --env-file .env.docker.secret config --quiet
docker compose --env-file .env.docker.secret up --build -d
docker compose --env-file .env.docker.secret ps
docker compose --env-file .env.docker.secret logs bot --tail 30
docker compose --env-file .env.docker.secret exec bot /app/.venv/bin/python bot.py --test "/health"
docker compose --env-file .env.docker.secret exec bot /app/.venv/bin/python bot.py --test "/scores lab-04"
curl -fsS http://localhost:42002/docs > /dev/null
```

The bot container runs as an unprivileged user and restarts unless stopped.
Both image builds use the committed root `uv.lock`. The backend build includes
both workspace manifests so uv can validate that lockfile. Secret files are
excluded from the Docker build context; Compose supplies runtime credentials.

Verify `/start`, `/health`, `/labs`, `/scores lab-04`, inline buttons, and
natural-language lab comparisons in Telegram. Check that the log contains
`Application started` and `[tool]` entries when tools run. Verify the missing
argument and unknown-command cases as well. After temporarily stopping the
backend, `/health` should return its actual connection error without a traceback;
restart the backend afterward.

If startup fails, inspect the bot log: HTTP 401 indicates credentials need
checking, HTTP 409 from Telegram can indicate another poller, connection failures
indicate a URL/network problem, and empty lab results usually require ETL sync.
Do not mark VM or Telegram acceptance checks complete until you have actually
run them. Each task still needs a classmate's PR review before merging to `main`.
