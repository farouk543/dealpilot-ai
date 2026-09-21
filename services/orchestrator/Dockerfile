FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.15 /uv /uvx /usr/local/bin/

WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
COPY shared /app/shared
COPY services/orchestrator /app/services/orchestrator

WORKDIR /app/services/orchestrator
RUN --mount=type=cache,target=/root/.cache/uv uv sync

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
