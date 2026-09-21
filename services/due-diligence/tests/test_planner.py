from dealpilot_shared import DDTaskType, Risk, RiskRegister, RiskSeverity

from app.planner import build_due_diligence


def _risk(**overrides) -> Risk:
    defaults = dict(
        category="documentaire",
        title="Document manquant : titre",
        severity=RiskSeverity.HIGH,
        evidence="e",
        impact="i",
        owner="investisseur",
        next_action="Demander le titre",
    )
    defaults.update(overrides)
    return Risk(**defaults)


def test_no_risks_gives_empty_ready_package():
    package = build_due_diligence(None)
    assert package.tasks == []
    assert package.unresolved_high_risk_tasks == 0
    assert package.decision_ready is True


def test_missing_document_risk_becomes_document_request_task():
    register = RiskRegister(risks=[_risk(title="Document manquant : titre de propriete")])
    package = build_due_diligence(register)
    assert len(package.tasks) == 1
    assert package.tasks[0].task_type == DDTaskType.DOCUMENT_REQUEST
    assert package.tasks[0].linked_risk_title == "Document manquant : titre de propriete"


def test_technical_risk_becomes_inspection_task():
    register = RiskRegister(
        risks=[
            _risk(
                category="technique",
                title="Indice visuel a verifier",
                next_action="Planifier une inspection professionnelle",
            )
        ]
    )
    package = build_due_diligence(register)
    assert package.tasks[0].task_type == DDTaskType.INSPECTION


def test_module_failure_risk_becomes_question_not_inspection():
    register = RiskRegister(
        risks=[
            _risk(
                category="technique",
                title="Echec d'analyse automatisee (vision_error)",
                next_action="Reessayer l'analyse ou traiter cette source manuellement.",
                severity=RiskSeverity.MEDIUM,
            )
        ]
    )
    package = build_due_diligence(register)
    assert package.tasks[0].task_type == DDTaskType.QUESTION


def test_financial_risk_becomes_professional_validation_task():
    register = RiskRegister(
        risks=[_risk(category="financier", title="DSCR faible", next_action="Revoir le financement")]
    )
    package = build_due_diligence(register)
    assert package.tasks[0].task_type == DDTaskType.PROFESSIONAL_VALIDATION


def test_contested_field_risk_becomes_question_task():
    register = RiskRegister(
        risks=[_risk(category="documentaire", title="Surface incoherent(e) entre sources", next_action="Verifier")]
    )
    package = build_due_diligence(register)
    assert package.tasks[0].task_type == DDTaskType.QUESTION


def test_high_severity_risk_blocks_decision_ready():
    register = RiskRegister(risks=[_risk(severity=RiskSeverity.HIGH)])
    package = build_due_diligence(register)
    assert package.unresolved_high_risk_tasks == 1
    assert package.decision_ready is False


def test_only_medium_risks_allows_decision_ready():
    register = RiskRegister(risks=[_risk(severity=RiskSeverity.MEDIUM)])
    package = build_due_diligence(register)
    assert package.unresolved_high_risk_tasks == 0
    assert package.decision_ready is True
