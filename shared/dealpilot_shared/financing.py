from pydantic import BaseModel


class FinancingAssumptions(BaseModel):
    down_payment_pct: float = 20.0
    interest_rate_pct: float = 4.0
    loan_term_years: int = 20
    vacancy_rate_pct: float = 5.0
    exit_cap_rate_pct: float | None = None
    holding_period_years: int = 10
    target_cap_rate_pct: float = 6.0
