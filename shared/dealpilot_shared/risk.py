from enum import Enum

from pydantic import BaseModel


class RiskSeverity(str, Enum):
    LOW = "faible"
    MEDIUM = "moyen"
    HIGH = "eleve"


class Risk(BaseModel):
    category: str
    title: str
    severity: RiskSeverity
    evidence: str
    impact: str
    owner: str
    next_action: str
    source_reference: str | None = None


class RiskRegister(BaseModel):
    risks: list[Risk]
