from fastapi import FastAPI
from pydantic import BaseModel

from dealpilot_shared import ExtractedFact, FinancingAssumptions, PropertyRecord, RiskRegister, UnderwritingResult
from dealpilot_shared.logging_utils import CorrelationIdMiddleware, configure_logging

from .strategy import build_offer

configure_logging("offer")

app = FastAPI(title="DealPilot AI — Offer")
app.add_middleware(CorrelationIdMiddleware)


class StrategizeRequest(BaseModel):
    property: PropertyRecord
    underwriting: UnderwritingResult | None = None
    document_facts: list[ExtractedFact] = []
    risk_register: RiskRegister | None = None
    assumptions: FinancingAssumptions


@app.post("/strategize")
def strategize(payload: StrategizeRequest) -> dict:
    offer = build_offer(
        property=payload.property,
        underwriting=payload.underwriting,
        document_facts=payload.document_facts,
        risk_register=payload.risk_register,
        assumptions=payload.assumptions,
    )
    return offer.model_dump(mode="json")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
