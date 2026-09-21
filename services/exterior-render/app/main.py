import json
import os
import subprocess
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from dealpilot_shared import BuildingDesignBrief
from dealpilot_shared.gpu_lock import gpu_lock
from dealpilot_shared.logging_utils import CorrelationIdMiddleware, configure_logging, get_logger

RENDERS_DIR = os.environ.get("RENDERS_DIR", "/data/renders")
PUBLIC_URL = os.environ.get("EXTERIOR_RENDER_PUBLIC_URL", "http://localhost:8025")
_SMOKE_TEST_SCRIPT = os.path.join(os.path.dirname(__file__), "blender_smoke_test.py")
_SCENE_BUILDER_SCRIPT = os.path.join(os.path.dirname(__file__), "scene_builder.py")

configure_logging("exterior-render")
_logger = get_logger(__name__)

os.makedirs(RENDERS_DIR, exist_ok=True)

app = FastAPI()
app.add_middleware(CorrelationIdMiddleware)
# model-viewer loads the .glb via fetch() (it has to, to parse the binary as
# WebGL geometry) from inside the Streamlit component's sandboxed iframe —
# unlike an <img> tag (used for the interior/facade renders), a fetch() is
# subject to CORS, and browsers silently fail it without this header.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])
app.mount("/images", StaticFiles(directory=RENDERS_DIR), name="images")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/render-test")
def render_test() -> dict:
    """Step 1 smoke test only: proves Blender + Cycles + GPU passthrough works
    in this environment. Not the real massing renderer."""
    filename = f"{uuid.uuid4().hex}.png"
    output_path = os.path.join(RENDERS_DIR, filename)
    with gpu_lock():
        result = subprocess.run(
            ["blender", "--background", "--factory-startup", "--python", _SMOKE_TEST_SCRIPT, "--", output_path],
            capture_output=True,
            text=True,
            timeout=120,
        )
    if result.returncode != 0 or "RENDER_OK" not in result.stdout:
        _logger.error("Blender smoke test failed: rc=%s stdout=%s stderr=%s", result.returncode, result.stdout, result.stderr)
        return {"error": "render failed", "stdout": result.stdout[-3000:], "stderr": result.stderr[-3000:]}

    device_line = next((line for line in result.stdout.splitlines() if line.startswith("CYCLES_DEVICE:")), "unknown")
    return {"image_url": f"{PUBLIC_URL}/images/{filename}", "device": device_line}


@app.post("/render")
def render_massing(request: BuildingDesignBrief) -> dict:
    """Cycles hero shot (HDRI, real recessed windows/door, garden) plus an
    animated glTF (construction-phase reveal) for <model-viewer>."""
    job_id = uuid.uuid4().hex
    brief_path = os.path.join(RENDERS_DIR, f"{job_id}.json")
    png_path = os.path.join(RENDERS_DIR, f"{job_id}.png")
    glb_path = os.path.join(RENDERS_DIR, f"{job_id}.glb")
    with open(brief_path, "w", encoding="utf-8") as f:
        json.dump(request.model_dump(), f)

    # Shared with interior-render's SDXL generation — see gpu_lock's docstring
    # for why a plain in-process lock can't serialize two separate containers
    # fighting over the same physical GPU.
    with gpu_lock():
        result = subprocess.run(
            ["blender", "--background", "--factory-startup", "--python", _SCENE_BUILDER_SCRIPT, "--", brief_path, png_path, glb_path],
            capture_output=True,
            text=True,
            timeout=180,
        )
    os.remove(brief_path)

    if result.returncode != 0 or "EXPORT_OK" not in result.stdout:
        _logger.error("Blender massing render failed: rc=%s stdout=%s stderr=%s", result.returncode, result.stdout, result.stderr)
        return {"error": "render failed", "stdout": result.stdout[-3000:], "stderr": result.stderr[-3000:]}

    def _stdout_value(prefix: str) -> str | None:
        line = next((l for l in result.stdout.splitlines() if l.startswith(prefix)), None)
        return line[len(prefix):].strip() if line else None

    phase_labels = json.loads(_stdout_value("PHASE_LABELS:") or "[]")
    return {
        "image_url": f"{PUBLIC_URL}/images/{job_id}.png",
        "model_url": f"{PUBLIC_URL}/images/{job_id}.glb",
        "viewer_url": f"{PUBLIC_URL}/viewer/{job_id}.glb",
        "device": _stdout_value("CYCLES_DEVICE:"),
        "phase_labels": phase_labels,
        "animation_fps": float(_stdout_value("ANIMATION_FPS:") or 24),
        "animation_end_frame": int(_stdout_value("ANIMATION_END_FRAME:") or 0),
    }


@app.get("/viewer/{filename}", response_class=HTMLResponse)
def viewer_page(filename: str) -> str:
    """Standalone <model-viewer> test page — step 3's way of visually
    verifying the construction-phase glTF animation without a frontend."""
    model_url = f"/images/{filename}"
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Exterior render viewer</title>
<script type="module" src="https://cdnjs.cloudflare.com/ajax/libs/model-viewer/3.5.0/model-viewer.min.js"></script>
<style>
  body {{ margin: 0; font-family: sans-serif; background: #eef2f5; }}
  model-viewer {{ width: 100vw; height: 80vh; background: #dce6ee; }}
  #controls {{ padding: 10px 16px; }}
</style>
</head>
<body>
<model-viewer id="mv" src="{model_url}" camera-controls auto-rotate shadow-intensity="1"></model-viewer>
<div id="controls">
  <button id="playBtn">Play construction sequence</button>
  <input id="scrub" type="range" min="0" max="1" step="0.01" value="1" style="width:60%">
</div>
<script>
  const mv = document.getElementById('mv');
  const scrub = document.getElementById('scrub');
  const playBtn = document.getElementById('playBtn');
  mv.addEventListener('load', () => {{
    mv.pause();
    mv.currentTime = mv.duration;
  }});
  scrub.addEventListener('input', () => {{
    mv.pause();
    mv.currentTime = mv.duration * parseFloat(scrub.value);
  }});
  playBtn.addEventListener('click', () => {{
    mv.currentTime = 0;
    mv.play();
  }});
</script>
</body>
</html>"""
