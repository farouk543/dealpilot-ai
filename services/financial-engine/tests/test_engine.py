import pytest

from app.amortization import monthly_payment, remaining_balance
from app.irr import compute_irr
from app.engine import run_underwriting
from dealpilot_shared import FinancingAssumptions


def test_monthly_payment_matches_textbook_example():
    # Classic reference case: $100,000 loan, 6% annual, 30 years -> $599.55/mo.
    assert monthly_payment(100_000, 6, 30) == pytest.approx(599.55, abs=0.01)


def test_monthly_payment_scales_linearly_with_loan_amount():
    base = monthly_payment(100_000, 6, 30)
    assert monthly_payment(400_000, 6, 30) == pytest.approx(base * 4, rel=1e-9)


def test_monthly_payment_zero_rate_is_simple_division():
    assert monthly_payment(120_000, 0, 10) == pytest.approx(1_000.0)


def test_remaining_balance_at_zero_months_equals_loan_amount():
    assert remaining_balance(200_000, 5, 20, 0) == pytest.approx(200_000)


def test_remaining_balance_at_full_term_is_zero():
    assert remaining_balance(200_000, 5, 20, 20 * 12) == pytest.approx(0.0, abs=0.01)


def test_irr_single_period_known_case():
    # -100 today, +110 in one period -> exactly 10% IRR.
    irr = compute_irr([-100, 110])
    assert irr == pytest.approx(0.10, abs=1e-4)


def test_irr_returns_none_when_never_profitable():
    assert compute_irr([-100, -10, -10, -10]) is None


def test_underwriting_base_scenario_hand_computed():
    assumptions = FinancingAssumptions(
        down_payment_pct=20,
        interest_rate_pct=6,
        loan_term_years=30,
        vacancy_rate_pct=5,
        exit_cap_rate_pct=8,
        holding_period_years=10,
    )
    result = run_underwriting(
        asking_price=500_000,
        monthly_rent=4_000,
        annual_charges=12_000,
        estimated_works=0,
        assumptions=assumptions,
    )
    base = next(s for s in result.scenarios if s.name == "base")

    expected_payment = monthly_payment(400_000, 6, 30)
    expected_annual_debt_service = expected_payment * 12
    expected_noi = 4_000 * 12 * 0.95 - 12_000  # 45600 - 12000 = 33600

    assert base.noi == pytest.approx(expected_noi, abs=0.01)
    assert base.cap_rate_pct == pytest.approx(expected_noi / 500_000 * 100, abs=0.01)
    assert base.annual_debt_service == pytest.approx(expected_annual_debt_service, abs=0.01)
    assert base.dscr == pytest.approx(expected_noi / expected_annual_debt_service, abs=0.001)
    assert base.cash_flow_before_tax == pytest.approx(expected_noi - expected_annual_debt_service, abs=0.01)
    assert base.cash_on_cash_pct == pytest.approx(
        (expected_noi - expected_annual_debt_service) / 100_000 * 100, abs=0.01
    )


def test_breakeven_rent_drop_matches_direct_computation():
    assumptions = FinancingAssumptions(
        down_payment_pct=20,
        interest_rate_pct=6,
        loan_term_years=30,
        vacancy_rate_pct=5,
        exit_cap_rate_pct=8,
        holding_period_years=10,
    )
    result = run_underwriting(
        asking_price=500_000,
        monthly_rent=4_000,
        annual_charges=12_000,
        estimated_works=0,
        assumptions=assumptions,
    )
    base = next(s for s in result.scenarios if s.name == "base")

    # At the breakeven gross rent, EGI == annual_debt_service + charges (DSCR = 1).
    breakeven_gross_rent = base.annual_debt_service + 12_000
    # EGI = gross_rent * (1 - vacancy) at base vacancy of 5%.
    breakeven_gross_rent /= 0.95
    expected_drop_pct = (1 - breakeven_gross_rent / base.gross_annual_rent) * 100

    assert result.breakeven.max_rent_drop_pct == pytest.approx(expected_drop_pct, abs=0.05)


def test_scenarios_are_ordered_pessimistic_to_optimistic_on_cash_flow():
    assumptions = FinancingAssumptions()
    result = run_underwriting(
        asking_price=500_000,
        monthly_rent=4_000,
        annual_charges=12_000,
        estimated_works=20_000,
        assumptions=assumptions,
    )
    by_name = {s.name: s for s in result.scenarios}
    assert by_name["baisse"].cash_flow_before_tax < by_name["base"].cash_flow_before_tax
    assert by_name["base"].cash_flow_before_tax < by_name["hausse"].cash_flow_before_tax
