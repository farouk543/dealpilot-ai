from app.development import run_development_proforma


def test_development_proforma_hand_computed():
    result = run_development_proforma(
        land_cost=200_000,
        construction_cost_per_m2=1_800,
        surface_to_build_m2=300,
        soft_costs_pct=10,
        estimated_exit_value=1_000_000,
    )
    # construction = 1800 * 300 = 540000
    # soft costs = 540000 * 0.10 = 54000
    # total = 200000 + 540000 + 54000 = 794000
    # margin = 1000000 - 794000 = 206000
    assert result.construction_cost_total == 540_000.0
    assert result.soft_costs_total == 54_000.0
    assert result.total_project_cost == 794_000.0
    assert result.margin == 206_000.0
    assert result.margin_pct == round(206_000 / 794_000 * 100, 2)


def test_negative_margin_when_costs_exceed_exit_value():
    result = run_development_proforma(
        land_cost=500_000,
        construction_cost_per_m2=2_000,
        surface_to_build_m2=300,
        soft_costs_pct=10,
        estimated_exit_value=900_000,
    )
    assert result.margin < 0


def test_zero_total_cost_gives_zero_margin_pct_not_crash():
    result = run_development_proforma(
        land_cost=0,
        construction_cost_per_m2=0,
        surface_to_build_m2=0,
        soft_costs_pct=0,
        estimated_exit_value=0,
    )
    assert result.margin_pct == 0.0
