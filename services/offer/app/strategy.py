from dealpilot_shared import (
    ExtractedFact,
    FinancingAssumptions,
    OfferStrategy,
    PropertyRecord,
    RiskRegister,
    RiskSeverity,
    UnderwritingResult,
)

from .loi import render_loi

_NO_CRITICAL_RISK_NOTE = "Aucune condition suspensive critique identifiee a ce stade ; revalider avant signature."


def _fact_float(facts: list[ExtractedFact], field_name: str) -> float | None:
    for fact in facts:
        if fact.field_name == field_name:
            try:
                return float(fact.value)
            except ValueError:
                return None
    return None


def _scenario_noi(underwriting: UnderwritingResult | None, name: str) -> float | None:
    if underwriting is None:
        return None
    scenario = next((s for s in underwriting.scenarios if s.name == name), None)
    return scenario.noi if scenario else None


def build_offer(
    *,
    property: PropertyRecord,
    underwriting: UnderwritingResult | None,
    document_facts: list[ExtractedFact],
    risk_register: RiskRegister | None,
    assumptions: FinancingAssumptions,
) -> OfferStrategy:
    asking_price = property.asking_price.resolved or property.asking_price.candidates[0].value
    target_cap_rate = assumptions.target_cap_rate_pct

    base_noi = _scenario_noi(underwriting, "base")
    stress_noi = _scenario_noi(underwriting, "baisse")

    max_price = (base_noi / (target_cap_rate / 100)) if base_noi else None
    stress_cap_price = (stress_noi / (target_cap_rate / 100)) if stress_noi else None

    market_median = _fact_float(document_facts, "market_value_median")

    price_candidates = [v for v in (market_median, max_price) if v is not None]
    target_price = min(price_candidates) if price_candidates else None
    if target_price is not None:
        target_price = min(target_price, asking_price)

    conditions: list[str] = []
    if risk_register is not None:
        for risk in risk_register.risks:
            if risk.severity == RiskSeverity.HIGH:
                conditions.append(f"{risk.title} — {risk.next_action}")
    if not conditions:
        conditions.append(_NO_CRITICAL_RISK_NOTE)

    rationale_parts = [
        f"Prix maximum = NOI de base ({base_noi}) / taux de capitalisation cible ({target_cap_rate}%)."
        if base_noi
        else "Prix maximum non calculable : NOI de base indisponible.",
    ]
    if market_median is not None:
        rationale_parts.append(f"Valeur de marche mediane (DVF) = {market_median}.")
    rationale_parts.append(
        f"Prix cible = min(valeur de marche, prix maximum), plafonne par le prix demande ({asking_price})."
    )
    rationale_parts.append(
        "Plafond en scenario de stress = NOI du scenario 'baisse' / meme taux de capitalisation cible."
    )

    return OfferStrategy(
        target_price=round(target_price, 2) if target_price is not None else None,
        max_price=round(max_price, 2) if max_price is not None else None,
        stress_cap_price=round(stress_cap_price, 2) if stress_cap_price is not None else None,
        target_cap_rate_pct=target_cap_rate,
        conditions=conditions,
        loi_draft=render_loi(property, target_price, conditions),
        rationale=" ".join(rationale_parts),
    )
