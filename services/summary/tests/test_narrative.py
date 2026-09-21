from app.narrative import _condense


def test_condense_extracts_base_scenario():
    deal_data = {
        "property": {"property_type": "Immeuble résidentiel", "location": "Lyon"},
        "current_step": "final_file",
        "underwriting": {
            "scenarios": [
                {"name": "base", "cap_rate_pct": 5.2},
                {"name": "baisse", "cap_rate_pct": 3.1},
            ]
        },
        "risk_register": {"risks": [{"title": "Risque X", "severity": "eleve"}]},
        "offer": {"target_price": 700000},
        "due_diligence": {"decision_ready": False, "unresolved_high_risk_tasks": 2},
    }
    condensed = _condense(deal_data)
    assert condensed["underwriting_base_scenario"]["cap_rate_pct"] == 5.2
    assert condensed["risks"] == [{"title": "Risque X", "severity": "eleve"}]
    assert condensed["due_diligence_ready"] is False
    assert condensed["unresolved_high_risk_tasks"] == 2


def test_condense_handles_missing_sections():
    condensed = _condense({"current_step": "intake"})
    assert condensed["underwriting_base_scenario"] is None
    assert condensed["risks"] == []
    assert condensed["due_diligence_ready"] is None
