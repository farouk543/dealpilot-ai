FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.15 /uv /uvx /usr/local/bin/

WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
COPY shared /app/shared
COPY services/interior-render /app/services/interior-render

WORKDIR /app/services/interior-render
RUN --mount=type=cache,target=/root/.cache/uv uv sync
# hf-xet's accelerated transfer protocol is throttled to near-zero on some
# networks; uninstalling it makes huggingface_hub fall back to plain HTTP
# downloads, which are dramatically faster here (~1.6 MB/s vs stalled).
RUN uv pip uninstall hf-xet

EXPOSE 8000
# Not "uv run": it re-syncs against pyproject.toml on every start and would
# reinstall hf-xet, undoing the uninstall above. This is a uv workspace, so
# the venv lives at the workspace root, not next to this service.
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
