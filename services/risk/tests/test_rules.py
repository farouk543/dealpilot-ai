from dealpilot_shared import (
    BreakevenAnalysis,
    ExtractedFact,
    FieldWithCandidates,
    FinancingAssumptions,
    Provenance,
    PropertyRecord,
    RiskSeverity,
    ScenarioResult,
    SourceType,
    UnderwritingResult,
)

from app.rules import (
    contested_field_risks,
    fact_based_risks,
    financial_risks,
    missing_document_risks,
    vacancy_risk,
)


def _field(value):
    f = FieldWithCandidates()
    f.add(value, Provenance(source_type=SourceType.USER_HYPOTHESIS, reference="test"))
    return f


def _property(**overrides) -> PropertyRecord:
    defaults = dict(
        id="p1",
        property_type="immeuble",
        location="Lyon",
        asking_price=_field(500_000),
        surface_m2=_field(300),
        units_total=_field(6),
        units_occupied=_field(6),
        monthly_rent=_field(4000),
        annual_charges=_field(12_000),
        estimated_works=_field(0),
        documents_received=[],
        documents_missing=[],
        photos_received=[],
    )
    defaults.update(overrides)
    return PropertyRecord(**defaults)


def test_contested_field_detected():
    prop = _property()
    prop.surface_m2.add(280, Provenance(source_type=SourceType.DOCUMENT, reference="plan.pdf"))
    risks = contested_field_risks(prop)
    assert any("surface" in r.title.lower() for r in risks)
    assert risks[0].severity == RiskSeverity.HIGH


def test_no_contested_field_no_risk():
    prop = _property()
    assert contested_field_risks(prop) == []


def test_declared_missing_document_flagged():
    prop = _property(documents_missing=["justificatifs fiscaux"], documents_received=["titre", "etat locatif"])
    risks = missing_document_risks(prop)
    assert any("justificatifs fiscaux" in r.title for r in risks)
    fiscal_risk = next(r for r in risks if "justificatifs fiscaux" in r.title)
    assert fiscal_risk.severity == RiskSeverity.HIGH


def test_undeclared_missing_titre_flagged():
    prop = _property(documents_received=["etat locatif"], documents_missing=[])
    risks = missing_document_risks(prop)
    assert any("titre" in r.title.lower() for r in risks)


def test_titre_present_no_risk():
    prop = _property(documents_received=["titre de propriete", "etat locatif"])
    risks = missing_document_risks(prop)
    assert not any("titre" in r.title.lower() for r in risks)


def test_prompt_injection_fact_flagged_high():
    facts = [
        ExtractedFact(
            field_name="security_flag",
            value="possible prompt injection attempt detected in bail.pdf",
            provenance=Provenance(source_type=SourceType.DOCUMENT, reference="bail.pdf"),
        )
    ]
    risks = fact_based_risks(facts)
    assert len(risks) == 1
    assert risks[0].severity == RiskSeverity.HIGH


def test_vision_needs_inspection_flagged():
    facts = [
        ExtractedFact(
            field_name="visual:humidite",
            value="Tache suspecte",
            provenance=Provenance(
                source_type=SourceType.VISION_ANALYSIS,
                reference="photo.jpg",
                confidence=0.9,
                note="needs_professional_inspection",
            ),
        )
    ]
    risks = fact_based_risks(facts)
    assert len(risks) == 1
    assert risks[0].severity == RiskSeverity.HIGH


def test_location_risk_severity_parsed_from_provenance_note():
    facts = [
        ExtractedFact(
            field_name="location_risk",
            value="Zone peu desservie par les transports en commun.",
            provenance=Provenance(
                source_type=SourceType.EXTERNAL_SOURCE,
                reference="Analyse LLM sur donnees OSM",
                note="severity:eleve",
            ),
        )
    ]
    risks = fact_based_risks(facts)
    assert len(risks) == 1
    assert risks[0].severity == RiskSeverity.HIGH
    assert risks[0].category == "marche"


def test_location_risk_defaults_to_medium_without_note():
    facts = [
        ExtractedFact(
            field_name="location_risk",
            value="Peu de commerces a proximite.",
            provenance=Provenance(source_type=SourceType.EXTERNAL_SOURCE, reference="OSM"),
        )
    ]
    risks = fact_based_risks(facts)
    assert risks[0].severity == RiskSeverity.MEDIUM


def test_vacancy_risk_detected():
    prop = _property(units_total=_field(6), units_occupied=_field(4))
    risk = vacancy_risk(prop)
    assert risk is not None
    assert "2" in risk.title


def test_no_vacancy_no_risk():
    prop = _property(units_total=_field(6), units_occupied=_field(6))
    assert vacancy_risk(prop) is None


def _scenario(name: str, dscr: float, cash_flow: float = 100.0) -> ScenarioResult:
    return ScenarioResult(
        name=name,
        gross_annual_rent=1,
        vacancy_loss=0,
        effective_gross_income=1,
        operating_expenses=0,
        noi=1,
        cap_rate_pct=1,
        annual_debt_service=1,
        cash_flow_before_tax=cash_flow,
        cash_on_cash_pct=1,
        dscr=dscr,
    )


def test_financial_risk_dscr_below_one_is_high():
    underwriting = UnderwritingResult(
        assumptions=FinancingAssumptions(),
        scenarios=[_scenario("base", 0.9), _scenario("baisse", 0.7), _scenario("hausse", 1.1)],
        breakeven=BreakevenAnalysis(),
    )
    risks = financial_risks(underwriting)
    high_risks = [r for r in risks if r.severity == RiskSeverity.HIGH]
    assert any("DSCR < 1" in r.title for r in high_risks)


def test_financial_risk_dscr_comfortable_no_risk():
    underwriting = UnderwritingResult(
        assumptions=FinancingAssumptions(),
        scenarios=[_scenario("base", 1.5), _scenario("baisse", 1.2), _scenario("hausse", 1.8)],
        breakeven=BreakevenAnalysis(
            max_rent_drop_pct=20, max_vacancy_rate_pct=25, max_interest_rate_pct=9
        ),
    )
    risks = financial_risks(underwriting)
    assert risks == []
