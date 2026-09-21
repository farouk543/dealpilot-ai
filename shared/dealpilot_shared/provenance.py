from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    DOCUMENT = "document"
    EXTERNAL_SOURCE = "external_source"
    CALCULATED = "calculated"
    USER_HYPOTHESIS = "user_hypothesis"
    VISION_ANALYSIS = "vision_analysis"


class Provenance(BaseModel):
    source_type: SourceType
    reference: str = Field(
        ..., description="Document id, URL, calc name, or 'user' depending on source_type"
    )
    note: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


T = TypeVar("T")


class SourcedValue(BaseModel, Generic[T]):
    value: T
    provenance: Provenance


class FieldWithCandidates(BaseModel, Generic[T]):
    """A critical field that may have conflicting values from different sources.

    Contradiction rule (see DealPilot spec section 6): never silently pick a
    value. Every candidate is kept with its provenance; `resolved` stays None
    and `contested` stays True until a human or a rule resolves it.
    """

    candidates: list[SourcedValue[T]] = Field(default_factory=list)
    resolved: T | None = None
    contested: bool = False

    def add(self, value: T, provenance: Provenance) -> None:
        self.candidates.append(SourcedValue(value=value, provenance=provenance))
        distinct_values = {c.value for c in self.candidates}
        self.contested = len(distinct_values) > 1
        self.resolved = value if not self.contested else None
