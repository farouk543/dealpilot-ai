from fastapi import FastAPI

from dealpilot_shared import LandConstraints
from dealpilot_shared.logging_utils import CorrelationIdMiddleware, configure_logging

from .feasibility import compute_feasibility

configure_logging("land-feasibility")

app = FastAPI(title="DealPilot AI — Land Feasibility")
app.add_middleware(CorrelationIdMiddleware)


@app.post("/feasibility")
def feasibility(constraints: LandConstraints) -> dict:
    return compute_feasibility(constraints).model_dump(mode="json")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
