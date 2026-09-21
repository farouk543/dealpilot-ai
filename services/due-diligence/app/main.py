from fastapi import FastAPI
from pydantic import BaseModel

from dealpilot_shared import RiskRegister
from dealpilot_shared.logging_utils import CorrelationIdMiddleware, configure_logging

from .planner import build_due_diligence

configure_logging("due-diligence")

app = FastAPI(title="DealPilot AI — Due Diligence")
app.add_middleware(CorrelationIdMiddleware)


class PlanRequest(BaseModel):
    risk_register: RiskRegister | None = None


@app.post("/plan")
def plan(payload: PlanRequest) -> dict:
    return build_due_diligence(payload.risk_register).model_dump(mode="json")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
