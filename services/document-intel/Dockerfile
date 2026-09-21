FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-fra poppler-utils \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.12.15 /uv /uvx /usr/local/bin/

WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
COPY shared /app/shared
COPY services/document-intel /app/services/document-intel

WORKDIR /app/services/document-intel
RUN --mount=type=cache,target=/root/.cache/uv uv sync

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
