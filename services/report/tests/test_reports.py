from app.pdf_report import build_pdf
from app.xlsx_report import build_xlsx

_SAMPLE_DEAL = {
    "deal_id": "test-123",
    "current_step": "final_file",
    "property": {"property_type": "Immeuble résidentiel", "location": "Lyon", "address": None},
    "underwriting": {
        "scenarios": [
            {
                "name": "base",
                "noi": 40000,
                "cap_rate_pct": 5.1,
                "cash_flow_before_tax": 12000,
                "cash_on_cash_pct": 7.2,
                "dscr": 1.4,
                "irr_pct": 9.1,
            }
        ]
    },
    "risk_register": {
        "risks": [
            {
                "category": "financier",
                "title": "Marge faible",
                "severity": "moyen",
                "evidence": "cap rate serré",
                "impact": "sensible aux hypothèses",
                "owner": "investisseur",
                "next_action": "revoir hypothèses",
            }
        ]
    },
    "offer": {
        "target_price": 700000,
        "max_price": 750000,
        "stress_cap_price": 680000,
        "target_cap_rate_pct": 6.0,
        "conditions": ["diagnostics à jour"],
        "loi_draft": "Lettre d'intention...",
        "rationale": "Basé sur les comparables DVF.",
    },
    "due_diligence": {
        "tasks": [
            {
                "task_type": "document_a_demander",
                "description": "Fournir diagnostics",
                "status": "ouvert",
                "severity_driver": "moyen",
                "linked_risk_title": "Marge faible",
            }
        ],
        "unresolved_high_risk_tasks": 0,
        "decision_ready": True,
        "audit_trail_note": "note",
    },
}


def test_build_pdf_produces_valid_pdf_bytes():
    pdf_bytes = build_pdf(_SAMPLE_DEAL)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500


def test_build_pdf_handles_missing_sections():
    pdf_bytes = build_pdf({"deal_id": "empty"})
    assert pdf_bytes.startswith(b"%PDF")


def test_build_xlsx_produces_valid_zip_bytes():
    xlsx_bytes = build_xlsx(_SAMPLE_DEAL)
    assert xlsx_bytes.startswith(b"PK")
    assert len(xlsx_bytes) > 500


def test_build_xlsx_handles_missing_sections():
    xlsx_bytes = build_xlsx({"deal_id": "empty"})
    assert xlsx_bytes.startswith(b"PK")
