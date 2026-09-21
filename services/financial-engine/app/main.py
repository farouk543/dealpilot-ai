from fastapi import FastAPI
from pydantic import BaseModel

from dealpilot_shared import FinancingAssumptions
from dealpilot_shared.logging_utils import CorrelationIdMiddleware, configure_logging

from .development import run_development_proforma
from .engine import run_underwriting

configure_logging("financial-engine")

app = FastAPI(title="DealPilot AI — Financial Engine")
app.add_middleware(CorrelationIdMiddleware)


class UnderwriteRequest(BaseModel):
    asking_price: float
    monthly_rent: float
    annual_charges: float
    estimated_works: float
    assumptions: FinancingAssumptions


class DevelopmentRequest(BaseModel):
    land_cost: float
    construction_cost_per_m2: float
    surface_to_build_m2: float
    soft_costs_pct: float = 12.0
    estimated_exit_value: float


@app.post("/underwrite")
def underwrite(payload: UnderwriteRequest) -> dict:
    result = run_underwriting(
        asking_price=payload.asking_price,
        monthly_rent=payload.monthly_rent,
        annual_charges=payload.annual_charges,
        estimated_works=payload.estimated_works,
        assumptions=payload.assumptions,
    )
    return result.model_dump(mode="json")


@app.post("/underwrite-development")
def underwrite_development(payload: DevelopmentRequest) -> dict:
    result = run_development_proforma(
        land_cost=payload.land_cost,
        construction_cost_per_m2=payload.construction_cost_per_m2,
        surface_to_build_m2=payload.surface_to_build_m2,
        soft_costs_pct=payload.soft_costs_pct,
        estimated_exit_value=payload.estimated_exit_value,
    )
    return result.model_dump(mode="json")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
