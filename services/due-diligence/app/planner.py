from dealpilot_shared import DDTaskType, DueDiligencePackage, DueDiligenceTask, Risk, RiskRegister, RiskSeverity


def _task_type_for(risk: Risk) -> DDTaskType:
    title_lower = risk.title.lower()
    next_action_lower = risk.next_action.lower()

    if "document manquant" in title_lower or "non fourni" in title_lower:
        return DDTaskType.DOCUMENT_REQUEST
    if "echec d'analyse" in title_lower:
        return DDTaskType.QUESTION
    if "inspection" in next_action_lower:
        return DDTaskType.INSPECTION
    if risk.category == "financier":
        return DDTaskType.PROFESSIONAL_VALIDATION
    return DDTaskType.QUESTION


def build_due_diligence(risk_register: RiskRegister | None) -> DueDiligencePackage:
    risks = risk_register.risks if risk_register else []

    tasks = [
        DueDiligenceTask(
            task_type=_task_type_for(risk),
            description=risk.next_action,
            severity_driver=risk.severity.value,
            linked_risk_title=risk.title,
        )
        for risk in risks
    ]

    unresolved_high = sum(1 for r in risks if r.severity == RiskSeverity.HIGH)

    audit_trail_note = (
        f"{len(tasks)} tache(s) de due diligence generee(s) a partir de {len(risks)} risque(s) identifie(s). "
        "Chaque tache reste reliee au risque (et donc a la source) qui l'a declenchee via linked_risk_title, "
        "formant la piste d'audit de l'annonce a la decision."
    )

    return DueDiligencePackage(
        tasks=tasks,
        unresolved_high_risk_tasks=unresolved_high,
        decision_ready=unresolved_high == 0,
        audit_trail_note=audit_trail_note,
    )
