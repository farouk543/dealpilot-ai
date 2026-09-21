from pydantic import BaseModel

from .financing import FinancingAssumptions


class ScenarioResult(BaseModel):
    name: str
    gross_annual_rent: float
    vacancy_loss: float
    effective_gross_income: float
    operating_expenses: float
    noi: float
    cap_rate_pct: float
    annual_debt_service: float
    cash_flow_before_tax: float
    cash_on_cash_pct: float
    dscr: float
    exit_value: float | None = None
    remaining_loan_balance_at_exit: float | None = None
    irr_pct: float | None = None


class BreakevenAnalysis(BaseModel):
    """Answers: which assumption must degrade for the base scenario to stop
    being viable (DSCR < 1)? Each field is the value at which DSCR = 1,
    all else held at the base scenario."""

    max_rent_drop_pct: float | None = None
    max_vacancy_rate_pct: float | None = None
    max_charges_increase_pct: float | None = None
    max_interest_rate_pct: float | None = None


class UnderwritingResult(BaseModel):
    assumptions: FinancingAssumptions
    scenarios: list[ScenarioResult]
    breakeven: BreakevenAnalysis
