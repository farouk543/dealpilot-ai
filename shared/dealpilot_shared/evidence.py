from pydantic import BaseModel

from .provenance import Provenance


class ExtractedFact(BaseModel):
    """A freeform fact pulled from a document that doesn't map to a fixed
    PropertyRecord field (lease dates, deposits, parties, obligations, or a
    security flag such as a detected prompt-injection attempt)."""

    field_name: str
    value: str
    provenance: Provenance
