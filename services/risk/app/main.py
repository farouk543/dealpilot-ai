from fastapi import FastAPI
from pydantic import BaseModel

from dealpilot_shared import ExtractedFact, PropertyRecord, RiskRegister, UnderwritingResult
from dealpilot_shared.logging_utils import CorrelationIdMiddleware, configure_logging

from .rules import (
    contested_field_risks,
    fact_based_risks,
    financial_risks,
    missing_document_risks,
    vacancy_risk,
)

configure_logging("risk")

app = FastAPI(title="DealPilot AI — Risk")
app.add_middleware(CorrelationIdMiddleware)


class AssessRequest(BaseModel):
    property: PropertyRecord
    document_facts: list[ExtractedFact] = []
    underwriting: UnderwritingResult | None = None


@app.post("/assess")
def assess(payload: AssessRequest) -> dict:
    risks = []
    risks.extend(contested_field_risks(payload.property))
    risks.extend(missing_document_risks(payload.property))
    risks.extend(fact_based_risks(payload.document_facts))
    vacancy = vacancy_risk(payload.property)
    if vacancy is not None:
        risks.append(vacancy)
    risks.extend(financial_risks(payload.underwriting))

    return RiskRegister(risks=risks).model_dump(mode="json")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
