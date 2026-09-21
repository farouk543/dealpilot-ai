from pydantic import BaseModel


class OfferStrategy(BaseModel):
    target_price: float | None = None
    max_price: float | None = None
    stress_cap_price: float | None = None
    target_cap_rate_pct: float
    conditions: list[str]
    loi_draft: str
    rationale: str
