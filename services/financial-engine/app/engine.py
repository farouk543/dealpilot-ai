from dealpilot_shared import BreakevenAnalysis, FinancingAssumptions, ScenarioResult, UnderwritingResult

from .amortization import monthly_payment, remaining_balance
from .irr import compute_irr

# Per-scenario deltas applied on top of the base FinancingAssumptions and
# base rent/charges. NOI is held constant over the holding period within a
# scenario (no rent-growth curve) to keep the model simple and auditable.
_SCENARIO_ADJUSTMENTS = {
    "base": {},
    "baisse": {"rent_pct": -10, "vacancy_pts": 5, "charges_pct": 10, "interest_pts": 1, "exit_cap_pts": 0.5},
    "hausse": {"rent_pct": 5, "vacancy_pts": -2, "charges_pct": -5, "interest_pts": -0.5, "exit_cap_pts": -0.5},
}


def _run_scenario(
    name: str,
    adjustments: dict,
    *,
    asking_price: float,
    monthly_rent: float,
    annual_charges: float,
    estimated_works: float,
    assumptions: FinancingAssumptions,
) -> ScenarioResult:
    rent = monthly_rent * (1 + adjustments.get("rent_pct", 0) / 100)
    vacancy_pct = max(assumptions.vacancy_rate_pct + adjustments.get("vacancy_pts", 0), 0.0)
    charges = annual_charges * (1 + adjustments.get("charges_pct", 0) / 100)
    interest_rate_pct = max(assumptions.interest_rate_pct + adjustments.get("interest_pts", 0), 0.01)

    gross_annual_rent = rent * 12
    vacancy_loss = gross_annual_rent * vacancy_pct / 100
    effective_gross_income = gross_annual_rent - vacancy_loss
    noi = effective_gross_income - charges

    down_payment = asking_price * assumptions.down_payment_pct / 100
    loan_amount = asking_price - down_payment
    total_cash_invested = down_payment + estimated_works

    payment = monthly_payment(loan_amount, interest_rate_pct, assumptions.loan_term_years)
    annual_debt_service = payment * 12

    cap_rate_pct = (noi / asking_price * 100) if asking_price else 0.0
    cash_flow = noi - annual_debt_service
    cash_on_cash_pct = (cash_flow / total_cash_invested * 100) if total_cash_invested else 0.0
    dscr = (noi / annual_debt_service) if annual_debt_service else float("inf")

    exit_cap_rate_pct = (assumptions.exit_cap_rate_pct or cap_rate_pct) + adjustments.get("exit_cap_pts", 0)
    exit_value = (noi / (exit_cap_rate_pct / 100)) if exit_cap_rate_pct > 0 else None

    n_months_held = assumptions.holding_period_years * 12
    loan_balance_at_exit = remaining_balance(loan_amount, interest_rate_pct, assumptions.loan_term_years, n_months_held)

    irr_pct = None
    if exit_value is not None and assumptions.holding_period_years >= 1 and total_cash_invested > 0:
        cashflows = [-total_cash_invested] + [cash_flow] * (assumptions.holding_period_years - 1)
        cashflows.append(cash_flow + exit_value - loan_balance_at_exit)
        irr = compute_irr(cashflows)
        irr_pct = irr * 100 if irr is not None else None

    return ScenarioResult(
        name=name,
        gross_annual_rent=round(gross_annual_rent, 2),
        vacancy_loss=round(vacancy_loss, 2),
        effective_gross_income=round(effective_gross_income, 2),
        operating_expenses=round(charges, 2),
        noi=round(noi, 2),
        cap_rate_pct=round(cap_rate_pct, 3),
        annual_debt_service=round(annual_debt_service, 2),
        cash_flow_before_tax=round(cash_flow, 2),
        cash_on_cash_pct=round(cash_on_cash_pct, 3),
        dscr=round(dscr, 3) if dscr != float("inf") else dscr,
        exit_value=round(exit_value, 2) if exit_value is not None else None,
        remaining_loan_balance_at_exit=round(loan_balance_at_exit, 2),
        irr_pct=round(irr_pct, 3) if irr_pct is not None else None,
    )


def _breakeven_interest_rate_pct(
    target_annual_debt_service: float, loan_amount: float, term_years: int
) -> float | None:
    if loan_amount <= 0:
        return None

    low, high = 0.0, 30.0

    def debt_service_at(rate_pct: float) -> float:
        return monthly_payment(loan_amount, rate_pct, term_years) * 12

    if debt_service_at(low) > target_annual_debt_service:
        return None  # even an interest-free loan exceeds NOI: not a rate problem
    if debt_service_at(high) < target_annual_debt_service:
        return high

    for _ in range(100):
        mid = (low + high) / 2
        if debt_service_at(mid) < target_annual_debt_service:
            low = mid
        else:
            high = mid
    return round((low + high) / 2, 3)


def _compute_breakeven(base: ScenarioResult, base_charges: float, loan_amount: float, term_years: int) -> BreakevenAnalysis:
    target_egi = base.annual_debt_service + base_charges  # EGI at which NOI == debt service (DSCR = 1)

    max_rent_drop_pct = None
    if base.gross_annual_rent > 0:
        vacancy_factor = base.effective_gross_income / base.gross_annual_rent if base.gross_annual_rent else 1
        breakeven_gross_rent = target_egi / vacancy_factor if vacancy_factor else None
        if breakeven_gross_rent is not None:
            max_rent_drop_pct = round((1 - breakeven_gross_rent / base.gross_annual_rent) * 100, 2)

    max_vacancy_rate_pct = None
    if base.gross_annual_rent > 0:
        max_vacancy_rate_pct = round((1 - target_egi / base.gross_annual_rent) * 100, 2)

    max_charges_increase_pct = None
    if base_charges > 0:
        breakeven_charges = base.effective_gross_income - base.annual_debt_service
        max_charges_increase_pct = round((breakeven_charges / base_charges - 1) * 100, 2)

    max_interest_rate_pct = _breakeven_interest_rate_pct(base.noi, loan_amount, term_years)

    return BreakevenAnalysis(
        max_rent_drop_pct=max_rent_drop_pct,
        max_vacancy_rate_pct=max_vacancy_rate_pct,
        max_charges_increase_pct=max_charges_increase_pct,
        max_interest_rate_pct=max_interest_rate_pct,
    )


def run_underwriting(
    *,
    asking_price: float,
    monthly_rent: float,
    annual_charges: float,
    estimated_works: float,
    assumptions: FinancingAssumptions,
) -> UnderwritingResult:
    scenarios = [
        _run_scenario(
            name,
            adjustments,
            asking_price=asking_price,
            monthly_rent=monthly_rent,
            annual_charges=annual_charges,
            estimated_works=estimated_works,
            assumptions=assumptions,
        )
        for name, adjustments in _SCENARIO_ADJUSTMENTS.items()
    ]

    base = scenarios[0]
    loan_amount = asking_price * (1 - assumptions.down_payment_pct / 100)
    breakeven = _compute_breakeven(base, annual_charges, loan_amount, assumptions.loan_term_years)

    return UnderwritingResult(assumptions=assumptions, scenarios=scenarios, breakeven=breakeven)
