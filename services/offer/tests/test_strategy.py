from dealpilot_shared import (
    BreakevenAnalysis,
    ExtractedFact,
    FieldWithCandidates,
    FinancingAssumptions,
    Provenance,
    PropertyRecord,
    Risk,
    RiskRegister,
    RiskSeverity,
    ScenarioResult,
    SourceType,
    UnderwritingResult,
)

from app.strategy import build_offer


def _field(value):
    f = FieldWithCandidates()
    f.add(value, Provenance(source_type=SourceType.USER_HYPOTHESIS, reference="test"))
    return f


def _property(asking_price=500_000) -> PropertyRecord:
    return PropertyRecord(
        id="p1",
        property_type="immeuble",
        location="Lyon",
        asking_price=_field(asking_price),
        surface_m2=_field(300),
        units_total=_field(6),
        units_occupied=_field(6),
        monthly_rent=_field(4000),
        annual_charges=_field(12_000),
        estimated_works=_field(0),
    )


def _underwriting(base_noi=30_000, stress_noi=20_000) -> UnderwritingResult:
    def scenario(name, noi):
        return ScenarioResult(
            name=name,
            gross_annual_rent=1,
            vacancy_loss=0,
            effective_gross_income=1,
            operating_expenses=0,
            noi=noi,
            cap_rate_pct=1,
            annual_debt_service=1,
            cash_flow_before_tax=1,
            cash_on_cash_pct=1,
            dscr=1,
        )

    return UnderwritingResult(
        assumptions=FinancingAssumptions(),
        scenarios=[scenario("base", base_noi), scenario("baisse", stress_noi), scenario("hausse", base_noi * 1.1)],
        breakeven=BreakevenAnalysis(),
    )


def test_max_price_from_base_noi_and_target_cap_rate():
    offer = build_offer(
        property=_property(),
        underwriting=_underwriting(base_noi=30_000),
        document_facts=[],
        risk_register=None,
        assumptions=FinancingAssumptions(target_cap_rate_pct=6.0),
    )
    assert offer.max_price == 30_000 / 0.06


def test_stress_cap_price_from_stress_noi():
    offer = build_offer(
        property=_property(),
        underwriting=_underwriting(base_noi=30_000, stress_noi=18_000),
        document_facts=[],
        risk_register=None,
        assumptions=FinancingAssumptions(target_cap_rate_pct=6.0),
    )
    assert offer.stress_cap_price == 18_000 / 0.06


def test_target_price_is_min_of_market_and_max_price_capped_by_asking():
    facts = [
        ExtractedFact(
            field_name="market_value_median",
            value="400000",
            provenance=Provenance(source_type=SourceType.EXTERNAL_SOURCE, reference="DVF"),
        )
    ]
    offer = build_offer(
        property=_property(asking_price=350_000),
        underwriting=_underwriting(base_noi=30_000),  # max_price = 500000 at 6%
        document_facts=facts,
        risk_register=None,
        assumptions=FinancingAssumptions(target_cap_rate_pct=6.0),
    )
    # market (400k) and max_price (500k) both exceed asking price (350k) -> capped at asking price
    assert offer.target_price == 350_000


def test_target_price_uses_lower_of_market_and_max_when_below_asking():
    facts = [
        ExtractedFact(
            field_name="market_value_median",
            value="280000",
            provenance=Provenance(source_type=SourceType.EXTERNAL_SOURCE, reference="DVF"),
        )
    ]
    offer = build_offer(
        property=_property(asking_price=500_000),
        underwriting=_underwriting(base_noi=30_000),  # max_price = 500000 at 6%
        document_facts=facts,
        risk_register=None,
        assumptions=FinancingAssumptions(target_cap_rate_pct=6.0),
    )
    assert offer.target_price == 280_000


def test_conditions_derived_from_high_severity_risks_only():
    risks = RiskRegister(
        risks=[
            Risk(
                category="documentaire",
                title="Titre de propriete non fourni",
                severity=RiskSeverity.HIGH,
                evidence="e",
                impact="i",
                owner="investisseur",
                next_action="Demander le titre",
            ),
            Risk(
                category="locatif",
                title="Vacance mineure",
                severity=RiskSeverity.MEDIUM,
                evidence="e",
                impact="i",
                owner="investisseur",
                next_action="Verifier",
            ),
        ]
    )
    offer = build_offer(
        property=_property(),
        underwriting=_underwriting(),
        document_facts=[],
        risk_register=risks,
        assumptions=FinancingAssumptions(),
    )
    assert len(offer.conditions) == 1
    assert "Titre de propriete" in offer.conditions[0]


def test_no_high_risk_gives_default_condition_note():
    offer = build_offer(
        property=_property(),
        underwriting=_underwriting(),
        document_facts=[],
        risk_register=RiskRegister(risks=[]),
        assumptions=FinancingAssumptions(),
    )
    assert len(offer.conditions) == 1
    assert "revalider" in offer.conditions[0].lower()


def test_loi_draft_is_explicitly_non_binding():
    offer = build_offer(
        property=_property(),
        underwriting=_underwriting(),
        document_facts=[],
        risk_register=None,
        assumptions=FinancingAssumptions(),
    )
    assert "non contraignante" in offer.loi_draft.lower()
    assert "ne constitue ni une offre ferme" in offer.loi_draft.lower()
