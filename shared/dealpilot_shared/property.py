from pydantic import BaseModel, Field

from .provenance import FieldWithCandidates


class PropertyRecord(BaseModel):
    """Normalized property file (fiche immobilière normalisée) — spec section 5."""

    id: str
    property_type: str
    location: str
    address: str | None = None
    asking_price: FieldWithCandidates[float]
    surface_m2: FieldWithCandidates[float]
    units_total: FieldWithCandidates[int]
    units_occupied: FieldWithCandidates[int]
    monthly_rent: FieldWithCandidates[float]
    annual_charges: FieldWithCandidates[float]
    estimated_works: FieldWithCandidates[float]
    documents_received: list[str] = Field(default_factory=list)
    documents_missing: list[str] = Field(default_factory=list)
    photos_received: list[str] = Field(default_factory=list)
