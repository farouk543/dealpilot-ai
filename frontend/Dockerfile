FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.15 /uv /uvx /usr/local/bin/

WORKDIR /app
COPY frontend /app

RUN --mount=type=cache,target=/root/.cache/uv uv sync

EXPOSE 8501
CMD ["uv", "run", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
