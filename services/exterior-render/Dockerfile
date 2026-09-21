FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.15 /uv /uvx /usr/local/bin/

# Blender's official Linux build still links against a handful of X11/OpenGL
# runtime libraries even in --background (headless) mode, despite never
# opening a window.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxrender1 libxi6 libxkbcommon0 libsm6 libxext6 libgl1 libxfixes3 \
    xz-utils curl \
    && rm -rf /var/lib/apt/lists/*

ARG BLENDER_MAJOR=5.2
ARG BLENDER_VERSION=5.2.2
RUN curl -fsSL "https://download.blender.org/release/Blender${BLENDER_MAJOR}/blender-${BLENDER_VERSION}-linux-x64.tar.xz" \
    -o /tmp/blender.tar.xz \
    && mkdir -p /opt/blender \
    && tar -xJf /tmp/blender.tar.xz -C /opt/blender --strip-components=1 \
    && rm /tmp/blender.tar.xz
ENV PATH="/opt/blender:${PATH}"

# CC0 (public domain) HDRI from Poly Haven, bundled at build time rather than
# fetched at request time — this project has already hit slow/unreliable
# downloads mid-request elsewhere (see RUNBOOK.md), and this file never
# changes, so there's no reason to pay that cost on every render.
RUN mkdir -p /opt/assets && curl -fsSL \
    "https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/1k/kloofendal_48d_partly_cloudy_1k.hdr" \
    -o /opt/assets/sky.hdr

WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
COPY shared /app/shared
COPY services/exterior-render /app/services/exterior-render

WORKDIR /app/services/exterior-render
RUN --mount=type=cache,target=/root/.cache/uv uv sync

EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
