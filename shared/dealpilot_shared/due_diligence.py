from enum import Enum

from pydantic import BaseModel


class DDTaskType(str, Enum):
    DOCUMENT_REQUEST = "document_a_demander"
    QUESTION = "question_ouverte"
    INSPECTION = "inspection_a_planifier"
    PROFESSIONAL_VALIDATION = "validation_professionnelle"


class DDTaskStatus(str, Enum):
    OPEN = "ouvert"
    RESOLVED = "resolu"


class DueDiligenceTask(BaseModel):
    task_type: DDTaskType
    description: str
    status: DDTaskStatus = DDTaskStatus.OPEN
    severity_driver: str | None = None  # eleve/moyen/faible, from the triggering risk
    linked_risk_title: str | None = None  # audit trail back to the fact/risk that triggered this task


class DueDiligencePackage(BaseModel):
    tasks: list[DueDiligenceTask]
    unresolved_high_risk_tasks: int
    decision_ready: bool
    audit_trail_note: str
