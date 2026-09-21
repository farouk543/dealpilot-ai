from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from .due_diligence import DueDiligencePackage
from .evidence import ExtractedFact
from .financing import FinancingAssumptions
from .offer import OfferStrategy
from .property import PropertyRecord
from .risk import RiskRegister
from .underwriting import UnderwritingResult


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WorkflowStep(str, Enum):
    INTAKE = "intake"
    NORMALIZATION = "normalization"
    DOCUMENT_INTELLIGENCE = "document_intelligence"
    VISUAL_ANALYSIS = "visual_analysis"
    MARKET_ANALYSIS = "market_analysis"
    FINANCIAL_UNDERWRITING = "financial_underwriting"
    RISK_ANALYSIS = "risk_analysis"
    OFFER_STRATEGY = "offer_strategy"
    DUE_DILIGENCE = "due_diligence"
    FINAL_FILE = "final_file"


class ApprovalRequest(BaseModel):
    step: WorkflowStep
    reason: str
    requested_at: datetime = Field(default_factory=_utcnow)
    resolved: bool = False
    approved: bool | None = None
    resolved_at: datetime | None = None


class DealState(BaseModel):
    """The orchestrator's view of one deal moving through the 10-step workflow."""

    deal_id: str
    created_at: datetime = Field(default_factory=_utcnow)
    current_step: WorkflowStep = WorkflowStep.INTAKE
    property: PropertyRecord | None = None
    document_facts: list[ExtractedFact] = Field(default_factory=list)
    financing_assumptions: FinancingAssumptions = Field(default_factory=FinancingAssumptions)
    underwriting: UnderwritingResult | None = None
    risk_register: RiskRegister | None = None
    offer: OfferStrategy | None = None
    due_diligence: DueDiligencePackage | None = None
    pending_approval: ApprovalRequest | None = None
    approval_history: list[ApprovalRequest] = Field(default_factory=list)
