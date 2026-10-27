ARG REGISTRY_PREFIX=harbor.pg.innopolis.university/docker-hub-cache/
FROM ${REGISTRY_PREFIX}astral/uv:0.12.23 AS uv
FROM ${REGISTRY_PREFIX}python:3.14.2-slim-bookworm AS builder
COPY --from=uv /uv /bin/uv

ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY backend/pyproject.toml backend/pyproject.toml
COPY bot/pyproject.toml bot/pyproject.toml
RUN uv sync --frozen --no-dev --package lms-bot
COPY bot bot

FROM ${REGISTRY_PREFIX}python:3.14.2-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd --system bot && useradd --system --gid bot --create-home bot
WORKDIR /app/bot
COPY --from=builder --chown=bot:bot /app/.venv /app/.venv
COPY --from=builder --chown=bot:bot /app/bot /app/bot
USER bot
CMD ["/app/.venv/bin/python", "bot.py"]
