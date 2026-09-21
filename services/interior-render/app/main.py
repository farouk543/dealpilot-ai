import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from dealpilot_shared import Facade360Request, InteriorRenderRequest
from dealpilot_shared.logging_utils import CorrelationIdMiddleware, configure_logging

from .generator import RENDERS_DIR, generate_facade_360, generate_interior, is_model_loaded

configure_logging("interior-render")

app = FastAPI(title="DealPilot AI — Interior Render")
app.add_middleware(CorrelationIdMiddleware)

os.makedirs(RENDERS_DIR, exist_ok=True)
app.mount("/images", StaticFiles(directory=RENDERS_DIR), name="images")


@app.post("/generate")
def generate(payload: InteriorRenderRequest) -> dict:
    result = generate_interior(payload)
    return result.model_dump(mode="json")


@app.post("/generate-360")
def generate_360(payload: Facade360Request) -> dict:
    result = generate_facade_360(payload)
    return result.model_dump(mode="json")


@app.get("/health")
def health() -> dict:
    # "status": "ok" means the process is up and can accept requests — it does
    # NOT mean a generation will be fast. model_loaded distinguishes "ready to
    # generate immediately" (weights resident on GPU) from "first request will
    # pay the one-time load cost" (or download cost, on a cold cache).
    return {"status": "ok", "model_loaded": is_model_loaded()}
