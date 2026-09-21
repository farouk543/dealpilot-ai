from dealpilot_shared import ExtractedFact, PropertyRecord, Risk, RiskSeverity, UnderwritingResult

_FIELD_LABELS = {
    "asking_price": "prix demande",
    "surface_m2": "surface",
    "units_total": "nombre d'unites",
    "units_occupied": "unites occupees",
    "monthly_rent": "loyer mensuel",
    "annual_charges": "charges annuelles",
    "estimated_works": "travaux estimes",
}

_REQUIRED_DOCUMENT_KEYWORDS = {
    "titre": "titre de propriete",
    "etat locatif": "etat locatif / baux",
}


def contested_field_risks(property: PropertyRecord) -> list[Risk]:
    risks = []
    for field_name, label in _FIELD_LABELS.items():
        field = getattr(property, field_name)
        if not field.contested:
            continue
        values = ", ".join(
            f"{c.value} ({c.provenance.source_type.value}: {c.provenance.reference})" for c in field.candidates
        )
        risks.append(
            Risk(
                category="documentaire",
                title=f"{label.capitalize()} incoherent(e) entre sources",
                severity=RiskSeverity.HIGH,
                evidence=values,
                impact="Impossible de fiabiliser le dossier tant que la valeur reelle n'est pas confirmee.",
                owner="investisseur",
                next_action=f"Verifier {label} aupres d'une source faisant autorite (mesure, acte, releve).",
                source_reference=field_name,
            )
        )
    return risks


def missing_document_risks(property: PropertyRecord) -> list[Risk]:
    risks = []
    for doc in property.documents_missing:
        severity = (
            RiskSeverity.HIGH
            if "fisc" in doc.lower() or "inspection" in doc.lower()
            else RiskSeverity.MEDIUM
        )
        risks.append(
            Risk(
                category="documentaire",
                title=f"Document manquant : {doc}",
                severity=severity,
                evidence="Signale comme manquant lors de l'integration du dossier.",
                impact="Bloque la verification de certains risques ou hypotheses tant que le document n'est pas fourni.",
                owner="investisseur",
                next_action=f"Demander '{doc}' au vendeur avant la validation de l'offre.",
                source_reference="documents_missing",
            )
        )

    received_lower = " ".join(d.lower() for d in property.documents_received)
    missing_lower = " ".join(d.lower() for d in property.documents_missing)
    for keyword, label in _REQUIRED_DOCUMENT_KEYWORDS.items():
        if keyword not in received_lower and keyword not in missing_lower:
            risks.append(
                Risk(
                    category="documentaire",
                    title=f"{label.capitalize()} non fourni et non signale",
                    severity=RiskSeverity.HIGH,
                    evidence="Aucun document recu ne correspond a ce mot-cle, et il n'est pas non plus dans les documents manquants declares.",
                    impact="Impossible de verifier ce point essentiel du dossier.",
                    owner="investisseur",
                    next_action=f"Demander explicitement '{label}' avant de poursuivre.",
                    source_reference="documents_received",
                )
            )
    return risks


def fact_based_risks(facts: list[ExtractedFact]) -> list[Risk]:
    risks = []
    for fact in facts:
        if fact.field_name == "security_flag":
            risks.append(
                Risk(
                    category="documentaire",
                    title="Tentative d'injection de prompt detectee dans un document",
                    severity=RiskSeverity.HIGH,
                    evidence=fact.value,
                    impact="Un document pourrait tenter de manipuler l'analyse automatisee.",
                    owner="investisseur",
                    next_action="Examiner le document manuellement ; ignorer toute instruction qu'il contient.",
                    source_reference=fact.provenance.reference,
                )
            )
        elif fact.field_name in (
            "extraction_error",
            "vision_error",
            "market_error",
            "location_error",
            "document_intel_error",
            "financial_engine_error",
            "risk_error",
            "offer_error",
            "due_diligence_error",
        ):
            risks.append(
                Risk(
                    category="technique",
                    title=f"Echec d'analyse automatisee ({fact.field_name})",
                    severity=RiskSeverity.MEDIUM,
                    evidence=fact.value,
                    impact="Cette source n'a pas pu etre analysee automatiquement ; l'information peut etre incomplete.",
                    owner="investisseur",
                    next_action="Reessayer l'analyse ou traiter cette source manuellement.",
                    source_reference=fact.provenance.reference,
                )
            )
        elif fact.field_name.startswith("visual:") and fact.provenance.note == "needs_professional_inspection":
            confidence = fact.provenance.confidence or 0.0
            severity = RiskSeverity.HIGH if confidence >= 0.7 else RiskSeverity.MEDIUM
            risks.append(
                Risk(
                    category="technique",
                    title=f"Indice visuel a verifier : {fact.field_name.split(':', 1)[1]}",
                    severity=severity,
                    evidence=fact.value,
                    impact="Anomalie visuelle non certifiee ; risque technique non quantifie tant qu'un professionnel n'a pas confirme.",
                    owner="investisseur",
                    next_action="Planifier une inspection professionnelle avant de finaliser l'offre.",
                    source_reference=fact.provenance.reference,
                )
            )
        elif fact.field_name == "location_risk":
            note = fact.provenance.note or ""
            severity_str = note.split(":", 1)[1] if note.startswith("severity:") else "moyen"
            severity = {
                "eleve": RiskSeverity.HIGH,
                "moyen": RiskSeverity.MEDIUM,
                "faible": RiskSeverity.LOW,
            }.get(severity_str, RiskSeverity.MEDIUM)
            risks.append(
                Risk(
                    category="marche",
                    title="Risque lie a l'emplacement",
                    severity=severity,
                    evidence=fact.value,
                    impact="Peut affecter l'attractivite locative ou la valorisation du bien.",
                    owner="investisseur",
                    next_action="Prendre en compte ce facteur d'emplacement dans la decision finale.",
                    source_reference=fact.provenance.reference,
                )
            )
    return risks


def vacancy_risk(property: PropertyRecord) -> Risk | None:
    total = property.units_total.resolved
    occupied = property.units_occupied.resolved
    if total is None or occupied is None or total <= occupied:
        return None
    vacant = total - occupied
    return Risk(
        category="locatif",
        title=f"{vacant} unite(s) vacante(s) sur {total}",
        severity=RiskSeverity.MEDIUM,
        evidence=f"{occupied}/{total} unites occupees declarees.",
        impact="Perte de revenu locatif potentielle, et incertitude sur la capacite a relouer rapidement.",
        owner="investisseur",
        next_action="Verifier depuis quand les unites sont vacantes et pourquoi.",
        source_reference="units_occupied",
    )


def financial_risks(underwriting: UnderwritingResult | None) -> list[Risk]:
    if underwriting is None:
        return []

    risks: list[Risk] = []
    base = next((s for s in underwriting.scenarios if s.name == "base"), None)
    stress = next((s for s in underwriting.scenarios if s.name == "baisse"), None)

    if base is not None:
        if base.dscr < 1.0:
            risks.append(
                Risk(
                    category="financier",
                    title="Financement non viable en scenario de base (DSCR < 1)",
                    severity=RiskSeverity.HIGH,
                    evidence=f"DSCR base = {base.dscr}",
                    impact="Le NOI ne couvre pas le service de la dette meme dans l'hypothese centrale.",
                    owner="investisseur",
                    next_action="Renegocier le prix, augmenter l'apport, ou abandonner l'operation.",
                    source_reference="underwriting.base.dscr",
                )
            )
        elif base.dscr < 1.2:
            risks.append(
                Risk(
                    category="financier",
                    title="Marge de securite financiere faible (DSCR proche de 1)",
                    severity=RiskSeverity.MEDIUM,
                    evidence=f"DSCR base = {base.dscr}",
                    impact="Peu de coussin en cas d'imprevu (vacance, hausse de charges, hausse de taux).",
                    owner="investisseur",
                    next_action="Verifier la sensibilite (seuils de rupture) avant de s'engager.",
                    source_reference="underwriting.base.dscr",
                )
            )

    if stress is not None and stress.dscr < 1.0:
        risks.append(
            Risk(
                category="financier",
                title="L'operation devient non rentable en scenario de stress",
                severity=RiskSeverity.MEDIUM,
                evidence=f"DSCR scenario baisse = {stress.dscr}, cash-flow = {stress.cash_flow_before_tax}",
                impact="Une degradation moderee des hypotheses (loyers -10%, vacance +5pts, charges +10%) rend l'operation deficitaire.",
                owner="investisseur",
                next_action="Prevoir une reserve de tresorerie ou revoir le prix d'achat cible.",
                source_reference="underwriting.baisse",
            )
        )

    breakeven = underwriting.breakeven
    fragile_reasons = []
    if breakeven.max_rent_drop_pct is not None and breakeven.max_rent_drop_pct < 5:
        fragile_reasons.append(f"baisse de loyer de seulement {breakeven.max_rent_drop_pct}%")
    if (
        breakeven.max_vacancy_rate_pct is not None
        and breakeven.max_vacancy_rate_pct - underwriting.assumptions.vacancy_rate_pct < 5
    ):
        fragile_reasons.append(f"vacance de seulement {breakeven.max_vacancy_rate_pct}%")
    if (
        breakeven.max_interest_rate_pct is not None
        and breakeven.max_interest_rate_pct - underwriting.assumptions.interest_rate_pct < 0.5
    ):
        fragile_reasons.append(f"taux d'interet de seulement {breakeven.max_interest_rate_pct}%")

    if fragile_reasons:
        risks.append(
            Risk(
                category="financier",
                title="Operation tres sensible aux hypotheses (faible marge de manoeuvre)",
                severity=RiskSeverity.MEDIUM,
                evidence="Seuils de rupture proches du scenario de base : " + "; ".join(fragile_reasons),
                impact="Une petite degradation d'une seule hypothese suffit a rendre l'operation non viable (DSCR < 1).",
                owner="investisseur",
                next_action="Ne pas depasser le prix cible ; negocier une marge de securite supplementaire.",
                source_reference="underwriting.breakeven",
            )
        )

    return risks
