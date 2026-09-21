from dealpilot_shared import DevelopmentProForma


def run_development_proforma(
    *,
    land_cost: float,
    construction_cost_per_m2: float,
    surface_to_build_m2: float,
    soft_costs_pct: float,
    estimated_exit_value: float,
) -> DevelopmentProForma:
    construction_cost_total = construction_cost_per_m2 * surface_to_build_m2
    soft_costs_total = construction_cost_total * soft_costs_pct / 100
    total_project_cost = land_cost + construction_cost_total + soft_costs_total

    margin = estimated_exit_value - total_project_cost
    margin_pct = (margin / total_project_cost * 100) if total_project_cost else 0.0

    return DevelopmentProForma(
        land_cost=round(land_cost, 2),
        construction_cost_per_m2=construction_cost_per_m2,
        surface_to_build_m2=surface_to_build_m2,
        construction_cost_total=round(construction_cost_total, 2),
        soft_costs_pct=soft_costs_pct,
        soft_costs_total=round(soft_costs_total, 2),
        total_project_cost=round(total_project_cost, 2),
        estimated_exit_value=round(estimated_exit_value, 2),
        margin=round(margin, 2),
        margin_pct=round(margin_pct, 2),
    )
