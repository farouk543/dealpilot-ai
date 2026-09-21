import os
import random

import requests
import streamlit as st
import streamlit.components.v1 as components

from facade_360_viewer import render_facade_360_html

ORCHESTRATOR_URL = os.environ.get("ORCHESTRATOR_URL", "http://orchestrator:8000")

DESIGN_TEMPLATES = [
    {
        "label": "🏠 Maison familiale traditionnelle",
        "brief": {
            "footprint_length_m": 10.0,
            "footprint_width_m": 8.0,
            "floors": 2,
            "floor_height_m": 3.0,
            "roof_type": "deux pans",
            "building_type": "maison individuelle",
            "architectural_style": "traditionnel",
        },
    },
    {
        "label": "🏢 Petit collectif moderniste",
        "brief": {
            "footprint_length_m": 16.0,
            "footprint_width_m": 10.0,
            "floors": 3,
            "floor_height_m": 3.0,
            "roof_type": "plat",
            "building_type": "petit collectif residentiel",
            "architectural_style": "moderniste",
        },
    },
    {
        "label": "🏛️ Immeuble haussmannien",
        "brief": {
            "footprint_length_m": 14.0,
            "footprint_width_m": 12.0,
            "floors": 4,
            "floor_height_m": 3.0,
            "roof_type": "quatre pans",
            "building_type": "collectif residentiel",
            "architectural_style": "haussmannien",
        },
    },
    {
        "label": "🏬 Local commercial contemporain",
        "brief": {
            "footprint_length_m": 12.0,
            "footprint_width_m": 9.0,
            "floors": 1,
            "floor_height_m": 3.5,
            "roof_type": "plat",
            "building_type": "local commercial",
            "architectural_style": "contemporain",
        },
    },
]

ARCHITECTURAL_STYLES = ["haussmannien", "moderniste", "contemporain", "traditionnel"]
ROOF_TYPES = ["plat", "deux pans", "quatre pans"]


def _describe_brief(brief: dict) -> str:
    return (
        f"{brief['building_type']}, style {brief['architectural_style']}, "
        f"{brief['footprint_length_m']}m x {brief['footprint_width_m']}m, "
        f"{brief['floors']} etage(s), toit {brief['roof_type']}."
    )


def _apply_design_template(brief: dict) -> None:
    st.session_state["land_brief"] = dict(brief)
    st.session_state.pop("land_facade_360", None)
    st.session_state["land_chat_history"] = [
        {"role": "user", "content": f"Je pars de ce modele : {_describe_brief(brief)}"},
        {
            "role": "assistant",
            "content": (
                "Modèle chargé. Tu peux me demander des ajustements (étages, toiture, style...) "
                "ou lancer directement la simulation 4D/5D ci-dessous."
            ),
        },
    ]
    st.session_state["land_suggestions"] = ["Ajouter un étage", "Essayer un autre style", "Changer la toiture"]


def _send_design_chat(user_text: str, feasibility_context: str) -> None:
    st.session_state["land_chat_history"].append({"role": "user", "content": user_text})
    try:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/land/chat",
            json={"history": st.session_state["land_chat_history"], "feasibility_context": feasibility_context},
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()
        st.session_state["land_chat_history"].append({"role": "assistant", "content": result["reply"]})
        st.session_state["land_suggestions"] = result.get("suggestions", [])
        if result.get("ready") and result.get("brief"):
            st.session_state["land_brief"] = result["brief"]
            st.session_state.pop("land_facade_360", None)
    except requests.RequestException as exc:
        st.error(f"Erreur de l'agent de conception : {exc}")


_RESIDENTIAL_ROOMS = [
    ("salon", "🛋️ Salon"),
    ("chambre", "🛏️ Chambre"),
    ("cuisine", "🍳 Cuisine"),
    ("salle de bain", "🛁 Salle de bain"),
    ("jardin", "🌳 Jardin"),
]
_COMMERCIAL_ROOMS = [
    ("vitrine", "🪟 Vitrine"),
    ("espace de vente", "🛍️ Espace de vente"),
    ("bureau", "💼 Bureau"),
    ("sanitaires", "🚻 Sanitaires"),
]
def _building_category(building_type: str) -> str:
    bt = (building_type or "").lower()
    if "commerc" in bt:
        return "commercial"
    if "mixte" in bt:
        return "mixte"
    return "residentiel"


def interior_room_types(building_type: str) -> list[tuple[str, str]]:
    """Only offers room buttons that make sense for the actual building being
    described — a commercial building is never offered a bedroom, a purely
    residential one is never offered a shopfront. Facade itself is generated
    in section 4 (360° view) now, not here — a separate single-shot facade
    button would use its own unrelated random seed and could contradict it."""
    category = _building_category(building_type)
    if category == "commercial":
        return [*_COMMERCIAL_ROOMS]
    if category == "mixte":
        return [*_COMMERCIAL_ROOMS, *_RESIDENTIAL_ROOMS]
    return [*_RESIDENTIAL_ROOMS]


def _generate_facade_360(brief: dict) -> None:
    with st.spinner("Génération de la vue 360° (8 angles, ~5-6 min)..."):
        try:
            response = requests.post(
                f"{ORCHESTRATOR_URL}/land/facade-360",
                json={
                    "architectural_style": brief.get("architectural_style", "contemporain"),
                    "building_type": brief.get("building_type", "residentiel"),
                    "floors": brief.get("floors"),
                    "roof_type": brief.get("roof_type"),
                },
                timeout=650,
            )
            response.raise_for_status()
            st.session_state["land_facade_360"] = response.json()
        except requests.RequestException as exc:
            st.session_state["land_facade_360"] = {"error": str(exc)}


def _generate_interior_render(room_type: str, brief: dict) -> None:
    st.session_state.setdefault("interior_renders", {})
    # Reuse the 360° facade's seed, when one has already been generated for
    # this building, so the room comes out visually consistent with it
    # (same color/material "family") instead of an unrelated random draw.
    facade_360 = st.session_state.get("land_facade_360") or {}
    seed = facade_360.get("seed")
    with st.spinner(f"Génération du rendu IA — {room_type}..."):
        try:
            response = requests.post(
                f"{ORCHESTRATOR_URL}/land/interior",
                json={
                    "room_type": room_type,
                    "architectural_style": brief.get("architectural_style", "contemporain"),
                    "building_type": brief.get("building_type", "residentiel"),
                    "floors": brief.get("floors"),
                    "roof_type": brief.get("roof_type"),
                    "seed": seed,
                },
                timeout=150,
            )
            response.raise_for_status()
            st.session_state["interior_renders"][room_type] = response.json()
        except requests.RequestException as exc:
            st.session_state["interior_renders"][room_type] = {"error": str(exc)}

st.set_page_config(page_title="DealPilot AI", layout="wide")

SEVERITY_ICON = {"eleve": "🔴", "moyen": "🟠", "faible": "🟢"}
SEVERITY_LABEL = {"eleve": "Élevé", "moyen": "Moyen", "faible": "Faible"}

FIELD_LABELS = {
    "asking_price": "Prix demandé",
    "surface_m2": "Surface (m²)",
    "units_total": "Nombre d'unités",
    "units_occupied": "Unités occupées",
    "monthly_rent": "Loyer mensuel",
    "annual_charges": "Charges annuelles",
    "estimated_works": "Travaux estimés",
}

TASK_TYPE_LABELS = {
    "document_a_demander": "📄 Document à demander",
    "question_ouverte": "❓ Question ouverte",
    "inspection_a_planifier": "🔍 Inspection à planifier",
    "validation_professionnelle": "✅ Validation professionnelle",
}


def submit_deal(form: dict, documents: list, photos: list) -> dict:
    data = {k: v for k, v in form.items() if v is not None}
    files = [("documents", (f.name, f.getvalue(), f.type)) for f in documents]
    files += [("photos", (f.name, f.getvalue(), f.type)) for f in photos]
    response = requests.post(f"{ORCHESTRATOR_URL}/deals", data=data, files=files, timeout=180)
    response.raise_for_status()
    return response.json()


def render_property(property: dict) -> None:
    st.subheader("1–2. Fiche immobilière normalisée")
    address_suffix = f" ({property['address']})" if property.get("address") else ""
    st.caption(f"{property['property_type']} — {property['location']}{address_suffix}")
    cols = st.columns(len(FIELD_LABELS))
    for col, (field_name, label) in zip(cols, FIELD_LABELS.items()):
        field = property[field_name]
        with col:
            if field["contested"]:
                st.metric(label, "⚠️ contesté")
                for c in field["candidates"]:
                    st.caption(f"{c['value']} ({c['provenance']['source_type']}: {c['provenance']['reference']})")
            else:
                st.metric(label, f"{field['resolved']:,.0f}".replace(",", " "))

    doc_col, missing_col, photo_col = st.columns(3)
    doc_col.write("**Documents reçus**")
    doc_col.write(", ".join(property["documents_received"]) or "_aucun_")
    missing_col.write("**Documents manquants (déclarés)**")
    missing_col.write(", ".join(property["documents_missing"]) or "_aucun_")
    photo_col.write("**Photos reçues**")
    photo_col.write(", ".join(property["photos_received"]) or "_aucune_")


def render_document_facts(facts: list) -> None:
    other_facts = [f for f in facts if not f["field_name"].startswith("location_")]
    if not other_facts:
        return
    st.subheader("3–5. Intelligence documentaire, analyse visuelle, marché")
    for fact in other_facts:
        prov = fact["provenance"]
        label = fact["field_name"]
        with st.expander(f"{label} — source: {prov['source_type']} ({prov['reference']})"):
            st.write(fact["value"])
            if prov.get("confidence") is not None:
                st.caption(f"Confiance: {prov['confidence']:.0%}")
            if prov.get("note"):
                st.caption(f"Note: {prov['note']}")


def render_location(facts: list) -> None:
    location_facts = [f for f in facts if f["field_name"].startswith("location_")]
    if not location_facts:
        return

    by_name = {f["field_name"]: f for f in location_facts}
    st.subheader("5bis. Intelligence de localisation")

    if "location_latitude" in by_name and "location_longitude" in by_name:
        lat = float(by_name["location_latitude"]["value"])
        lon = float(by_name["location_longitude"]["value"])
        st.map([{"lat": lat, "lon": lon}], zoom=15)

    counts = {
        f["field_name"].split(":", 1)[1]: f["value"]
        for f in location_facts
        if f["field_name"].startswith("location_count:")
    }
    if counts:
        cols = st.columns(len(counts))
        for col, (category, count) in zip(cols, counts.items()):
            col.metric(category.replace("_", " ").capitalize(), count)

    if "location_vibrancy_index" in by_name:
        index = int(by_name["location_vibrancy_index"]["value"])
        st.progress(
            min(index, 100) / 100,
            text=f"Indice de dynamisme du quartier (indicatif, non validé scientifiquement) : {index}/100",
        )

    if "location_context" in by_name:
        st.write(by_name["location_context"]["value"])

    opportunities = [f for f in location_facts if f["field_name"].startswith("location_opportunity:")]
    if opportunities:
        st.write("**Opportunités identifiées**")
        for f in opportunities:
            conf = f["provenance"].get("confidence")
            conf_text = f" _(confiance {conf:.0%})_" if conf is not None else ""
            st.write(f"- {f['value']}{conf_text}")

    for f in location_facts:
        if f["field_name"] == "location_error":
            st.warning(f["value"])


def render_underwriting(underwriting: dict | None) -> None:
    if underwriting is None:
        return
    st.subheader("6. Souscription financière déterministe")
    scenario_rows = []
    for s in underwriting["scenarios"]:
        scenario_rows.append(
            {
                "Scénario": s["name"],
                "NOI": s["noi"],
                "Cap rate %": s["cap_rate_pct"],
                "Service dette annuel": s["annual_debt_service"],
                "Cash-flow": s["cash_flow_before_tax"],
                "Cash-on-cash %": s["cash_on_cash_pct"],
                "DSCR": s["dscr"],
                "IRR %": s["irr_pct"],
            }
        )
    st.table(scenario_rows)

    b = underwriting["breakeven"]
    st.caption(
        "**Seuils de rupture (DSCR = 1)** — "
        f"baisse de loyer max: {b['max_rent_drop_pct']}% · "
        f"vacance max: {b['max_vacancy_rate_pct']}% · "
        f"hausse de charges max: {b['max_charges_increase_pct']}% · "
        f"taux d'intérêt max: {b['max_interest_rate_pct']}%"
    )


def render_risks(risk_register: dict | None) -> None:
    if risk_register is None:
        return
    st.subheader("7. Registre des risques")
    for risk in risk_register["risks"]:
        icon = SEVERITY_ICON.get(risk["severity"], "•")
        with st.expander(f"{icon} [{risk['category']}] {risk['title']}"):
            st.write(f"**Preuve** : {risk['evidence']}")
            st.write(f"**Impact** : {risk['impact']}")
            st.write(f"**Propriétaire** : {risk['owner']}")
            st.write(f"**Prochaine action** : {risk['next_action']}")


def render_offer(offer: dict | None) -> None:
    if offer is None:
        return
    st.subheader("8. Stratégie d'offre")
    c1, c2, c3 = st.columns(3)
    c1.metric("Prix cible", f"{offer['target_price']:,.0f} €".replace(",", " ") if offer["target_price"] else "—")
    c2.metric("Prix maximum", f"{offer['max_price']:,.0f} €".replace(",", " ") if offer["max_price"] else "—")
    c3.metric(
        "Plafond scénario de stress",
        f"{offer['stress_cap_price']:,.0f} €".replace(",", " ") if offer["stress_cap_price"] else "—",
    )
    st.caption(offer["rationale"])

    st.write("**Conditions suspensives**")
    for c in offer["conditions"]:
        st.write(f"- {c}")

    with st.expander("Projet de lettre d'intention (non contraignant)"):
        st.text_area("LOI", offer["loi_draft"], height=220, label_visibility="collapsed")


def render_due_diligence(dd: dict | None) -> None:
    if dd is None:
        return
    st.subheader("9. Salle de données et due diligence")
    if dd["decision_ready"]:
        st.success("Aucun risque élevé non résolu — dossier prêt pour une décision.")
    else:
        st.warning(
            f"{dd['unresolved_high_risk_tasks']} tâche(s) liée(s) à un risque élevé encore ouverte(s) — "
            "décision d'achat non recommandée en l'état."
        )
    for task in dd["tasks"]:
        icon = SEVERITY_ICON.get(task["severity_driver"], "•")
        label = TASK_TYPE_LABELS.get(task["task_type"], task["task_type"])
        st.checkbox(
            f"{icon} {label} — {task['description']}  _(← {task['linked_risk_title']})_",
            key=f"task_{task['linked_risk_title']}_{task['description']}",
        )
    st.caption(dd["audit_trail_note"])


def render_final_decision(deal: dict) -> None:
    st.subheader("10. Dossier final — décision")
    dd = deal.get("due_diligence")
    ready = dd["decision_ready"] if dd else False
    if not ready:
        st.info(
            "Le système ne prend pas la décision d'achat à votre place. "
            "Les points ci-dessus doivent être vérifiés avant toute validation."
        )
    validated = st.checkbox(
        "Je (l'investisseur) ai revu les risques, l'analyse financière et les conditions ci-dessus, "
        "et je valide la stratégie d'offre pour transmission.",
        key="human_validation",
    )
    if validated:
        st.success("Validation humaine enregistrée pour cette session. Vous pouvez transmettre la LOI.")


def render_export_and_summary(deal_id: str) -> None:
    st.subheader("11. Export et résumé")
    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("📄 Générer le PDF", key="gen_pdf"):
            with st.spinner("Génération du PDF..."):
                try:
                    resp = requests.get(f"{ORCHESTRATOR_URL}/deals/{deal_id}/export.pdf", timeout=30)
                    resp.raise_for_status()
                    st.session_state["pdf_bytes"] = resp.content
                except requests.RequestException as exc:
                    st.error(f"Erreur export PDF : {exc}")
        if st.session_state.get("pdf_bytes"):
            st.download_button(
                "⬇️ Télécharger le PDF", st.session_state["pdf_bytes"], file_name=f"dealpilot_{deal_id}.pdf",
                mime="application/pdf",
            )

    with c2:
        if st.button("📊 Générer l'Excel", key="gen_xlsx"):
            with st.spinner("Génération de l'Excel..."):
                try:
                    resp = requests.get(f"{ORCHESTRATOR_URL}/deals/{deal_id}/export.xlsx", timeout=30)
                    resp.raise_for_status()
                    st.session_state["xlsx_bytes"] = resp.content
                except requests.RequestException as exc:
                    st.error(f"Erreur export Excel : {exc}")
        if st.session_state.get("xlsx_bytes"):
            st.download_button(
                "⬇️ Télécharger l'Excel", st.session_state["xlsx_bytes"], file_name=f"dealpilot_{deal_id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    with c3:
        if st.button("💬 Résumé en langage simple", key="gen_summary"):
            with st.spinner("Génération du résumé..."):
                try:
                    resp = requests.get(f"{ORCHESTRATOR_URL}/deals/{deal_id}/summary", timeout=30)
                    resp.raise_for_status()
                    result = resp.json()
                    st.session_state["summary_text"] = result.get("narrative") or result.get("error")
                except requests.RequestException as exc:
                    st.error(f"Erreur résumé : {exc}")

    if st.session_state.get("summary_text"):
        st.info(st.session_state["summary_text"])


def render_counter_offer(deal: dict) -> None:
    if deal.get("offer") is None or deal.get("underwriting") is None:
        return
    st.subheader("12. Simulateur de contre-offre")
    st.caption(
        "Simule l'impact d'un prix de contre-offre sur la rentabilité, en réutilisant le même moteur "
        "financier déterministe que l'analyse initiale."
    )
    current_price = deal["property"]["asking_price"]["resolved"] or deal["property"]["asking_price"]["candidates"][0]["value"]
    counter_price = st.number_input(
        "Prix de contre-offre (€)", min_value=0.0, value=float(current_price), step=1000.0, key="counter_price"
    )
    if st.button("Simuler", key="simulate_counter"):
        with st.spinner("Simulation en cours..."):
            try:
                resp = requests.post(
                    f"{ORCHESTRATOR_URL}/deals/{deal['deal_id']}/counter-offer",
                    json={"counter_price": counter_price},
                    timeout=30,
                )
                resp.raise_for_status()
                st.session_state["counter_offer_result"] = resp.json()
            except requests.RequestException as exc:
                st.error(f"Erreur simulation : {exc}")

    result = st.session_state.get("counter_offer_result")
    if result:
        orig = result["original_base_scenario"]
        new = result["updated_base_scenario"]
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**Prix initial : {result['original_price']:,.0f} €**".replace(",", " "))
            st.metric("Cap rate", f"{orig['cap_rate_pct']:.2f} %")
            st.metric("Cash-on-cash", f"{orig['cash_on_cash_pct']:.2f} %")
            st.metric("DSCR", f"{orig['dscr']:.2f}" if isinstance(orig["dscr"], (int, float)) else orig["dscr"])
        with c2:
            st.write(f"**Contre-offre : {result['counter_price']:,.0f} €**".replace(",", " "))
            st.metric(
                "Cap rate", f"{new['cap_rate_pct']:.2f} %", delta=f"{new['cap_rate_pct'] - orig['cap_rate_pct']:+.2f}"
            )
            st.metric(
                "Cash-on-cash",
                f"{new['cash_on_cash_pct']:.2f} %",
                delta=f"{new['cash_on_cash_pct'] - orig['cash_on_cash_pct']:+.2f}",
            )
            st.metric("DSCR", f"{new['dscr']:.2f}" if isinstance(new["dscr"], (int, float)) else new["dscr"])
        st.info(result["recommendation"])


def render_comparison() -> None:
    st.subheader("13. Comparaison multi-biens")
    compared = st.session_state.setdefault("compared_deal_ids", [])
    deal = st.session_state.get("deal")

    c1, c2 = st.columns([1, 1])
    with c1:
        if deal and st.button("➕ Ajouter ce dossier à la comparaison", key="add_to_compare"):
            if deal["deal_id"] not in compared:
                compared.append(deal["deal_id"])
    with c2:
        if compared and st.button("🗑️ Vider la comparaison", key="clear_compare"):
            st.session_state["compared_deal_ids"] = []
            compared = []

    if not compared:
        st.caption("Aucun dossier ajouté à la comparaison pour l'instant.")
        return

    try:
        resp = requests.get(f"{ORCHESTRATOR_URL}/deals/compare", params={"ids": ",".join(compared)}, timeout=30)
        resp.raise_for_status()
        rows = resp.json()["deals"]
    except requests.RequestException as exc:
        st.error(f"Erreur comparaison : {exc}")
        return

    table_rows = []
    for r in rows:
        if r.get("error"):
            table_rows.append({"Dossier": r["deal_id"][:8], "Erreur": r["error"]})
            continue
        table_rows.append(
            {
                "Dossier": r["deal_id"][:8],
                "Type": r.get("property_type"),
                "Localisation": r.get("location"),
                "Prix demandé": r.get("asking_price"),
                "Cap rate %": r.get("cap_rate_pct"),
                "Cash-on-cash %": r.get("cash_on_cash_pct"),
                "DSCR": r.get("dscr"),
                "Prix cible offre": r.get("offer_target_price"),
                "Risques": r.get("risk_count"),
                "Prêt décision": r.get("decision_ready"),
            }
        )
    st.table(table_rows)


def render_investor_flow() -> None:
    with st.sidebar:
        st.header("Nouveau dossier")
        with st.form("intake_form"):
            property_type = st.text_input("Type de bien", "Immeuble résidentiel")
            location = st.text_input("Localisation (ville)", "Lyon")
            address = st.text_input(
                "Adresse complète (optionnel, améliore l'analyse d'emplacement)",
                placeholder="ex: 10 Rue de la République, Lyon",
            )
            listing_url = st.text_input("URL de l'annonce (optionnel)")
            asking_price = st.number_input("Prix demandé (€)", min_value=0.0, value=780_000.0, step=1000.0)
            surface_m2 = st.number_input("Surface (m²)", min_value=0.0, value=410.0, step=1.0)
            units_total = st.number_input("Nombre d'unités", min_value=1, value=6, step=1)
            units_occupied = st.number_input("Unités occupées", min_value=0, value=5, step=1)
            monthly_rent = st.number_input("Loyer mensuel total (€)", min_value=0.0, value=5_800.0, step=50.0)
            annual_charges = st.number_input("Charges annuelles (€)", min_value=0.0, value=19_000.0, step=100.0)
            estimated_works = st.number_input("Travaux estimés (€)", min_value=0.0, value=65_000.0, step=500.0)
            known_missing_documents = st.text_input(
                "Documents connus comme manquants (séparés par des virgules)", "justificatifs fiscaux"
            )

            st.markdown("**Hypothèses de financement**")
            down_payment_pct = st.slider("Apport (%)", 0.0, 100.0, 20.0)
            interest_rate_pct = st.slider("Taux d'intérêt (%)", 0.0, 10.0, 4.2, step=0.1)
            loan_term_years = st.number_input("Durée du prêt (années)", min_value=1, value=20, step=1)
            vacancy_rate_pct = st.slider("Taux de vacance supposé (%)", 0.0, 30.0, 5.0)
            holding_period_years = st.number_input("Durée de détention (années)", min_value=1, value=10, step=1)
            target_cap_rate_pct = st.slider("Taux de capitalisation cible (%)", 1.0, 15.0, 6.0, step=0.1)

            documents = st.file_uploader("Documents (PDF, texte, images)", accept_multiple_files=True)
            photos = st.file_uploader("Photos", accept_multiple_files=True, type=["jpg", "jpeg", "png"])

            submitted = st.form_submit_button("Analyser le dossier")

    if submitted:
        form = {
            "property_type": property_type,
            "location": location,
            "address": address or None,
            "listing_url": listing_url or None,
            "asking_price": asking_price,
            "surface_m2": surface_m2,
            "units_total": int(units_total),
            "units_occupied": int(units_occupied),
            "monthly_rent": monthly_rent,
            "annual_charges": annual_charges,
            "estimated_works": estimated_works,
            "known_missing_documents": known_missing_documents,
            "down_payment_pct": down_payment_pct,
            "interest_rate_pct": interest_rate_pct,
            "loan_term_years": int(loan_term_years),
            "vacancy_rate_pct": vacancy_rate_pct,
            "holding_period_years": int(holding_period_years),
            "target_cap_rate_pct": target_cap_rate_pct,
        }
        with st.spinner("Analyse du dossier en cours (documents, vision, marché, finance, risques, offre)..."):
            try:
                st.session_state["deal"] = submit_deal(form, documents or [], photos or [])
                st.session_state["deal_error"] = None
            except requests.HTTPError as exc:
                st.session_state["deal"] = None
                st.session_state["deal_error"] = (
                    f"Erreur du serveur : {exc.response.status_code} — {exc.response.text}"
                )
            except requests.RequestException as exc:
                st.session_state["deal"] = None
                st.session_state["deal_error"] = f"Impossible de contacter l'orchestrator : {exc}"

    if st.session_state.get("deal_error"):
        st.error(st.session_state["deal_error"])

    deal = st.session_state.get("deal")
    if deal:
        st.success(f"Dossier {deal['deal_id']} — étape actuelle : {deal['current_step']}")
        render_property(deal["property"])
        render_document_facts(deal.get("document_facts", []))
        render_location(deal.get("document_facts", []))
        render_underwriting(deal.get("underwriting"))
        render_risks(deal.get("risk_register"))
        render_offer(deal.get("offer"))
        render_due_diligence(deal.get("due_diligence"))
        render_final_decision(deal)
        render_export_and_summary(deal["deal_id"])
        render_counter_offer(deal)
    else:
        st.info("Remplis le formulaire à gauche et lance l'analyse d'un premier dossier.")

    render_comparison()


def render_promoter_flow(role: str) -> None:
    st.info(
        "Module terrain / construction neuve — pour "
        + ("promoteurs" if role == "promoteur" else "particuliers souhaitant construire")
        + ". La visualisation 3D est une **étude de volume indicative** (gabarit), "
        "pas une conception architecturale."
    )

    with st.sidebar:
        st.header("1. Faisabilité du terrain")
        with st.form("land_form"):
            address = st.text_input(
                "Adresse du terrain (optionnel — interroge le vrai zonage PLU officiel)",
                placeholder="ex: 1 place Bellecour, Lyon",
            )
            surface_terrain_m2 = st.number_input("Surface du terrain (m²)", min_value=10.0, value=500.0, step=10.0)
            emprise_au_sol_max_pct = st.slider("Emprise au sol maximale autorisée (%)", 5.0, 100.0, 40.0)
            hauteur_max_m = st.number_input("Hauteur maximale autorisée (m)", min_value=2.0, value=9.0, step=0.5)
            floor_height_m = st.number_input("Hauteur sous plafond par étage (m)", min_value=2.0, value=3.0, step=0.1)
            land_submitted = st.form_submit_button("Calculer la faisabilité")

    if land_submitted:
        try:
            response = requests.post(
                f"{ORCHESTRATOR_URL}/land/feasibility",
                json={
                    "surface_terrain_m2": surface_terrain_m2,
                    "emprise_au_sol_max_pct": emprise_au_sol_max_pct,
                    "hauteur_max_m": hauteur_max_m,
                    "floor_height_m": floor_height_m,
                    "address": address or None,
                },
                timeout=30,
            )
            response.raise_for_status()
            st.session_state["land_feasibility"] = response.json()
        except requests.RequestException as exc:
            st.error(f"Erreur de calcul de faisabilité : {exc}")

    feasibility = st.session_state.get("land_feasibility")
    if feasibility:
        st.subheader("Faisabilité du terrain")
        c1, c2, c3 = st.columns(3)
        c1.metric("Emprise au sol constructible", f"{feasibility['buildable_footprint_m2']:.0f} m²")
        c2.metric("Étages maximum", feasibility["max_floors"])
        c3.metric("Surface de plancher max", f"{feasibility['max_buildable_surface_m2']:.0f} m²")
        st.caption(feasibility["assumptions_note"])
        real_zoning = feasibility.get("real_zoning")
        if real_zoning:
            st.success(
                f"📍 Zone officielle (Géoportail de l'Urbanisme) : **{real_zoning['zone_code']}** "
                f"({real_zoning['zone_type']}) — {real_zoning['description']}"
            )
            checklist = feasibility.get("administrative_checklist") or []
            if checklist:
                with st.expander("📋 Démarches administratives typiques pour cette zone (indicatif)"):
                    for step in checklist:
                        st.write(f"**{step['label']}**")
                        st.caption(step["description"])
                    st.caption(
                        "Information générale dérivée du type de zone — ne remplace pas une vérification "
                        "auprès du service urbanisme de la commune."
                    )

        st.subheader("2. Pro forma de promotion")
        with st.form("proforma_form"):
            land_cost = st.number_input("Coût du terrain (€)", min_value=0.0, value=200_000.0, step=5_000.0)
            construction_cost_per_m2 = st.number_input(
                "Coût de construction (€/m²)", min_value=0.0, value=1_800.0, step=50.0
            )
            surface_to_build_m2 = st.number_input(
                "Surface de plancher à construire (m²)",
                min_value=0.0,
                value=float(feasibility["max_buildable_surface_m2"]),
                step=10.0,
            )
            soft_costs_pct = st.slider("Frais annexes (architecte, permis...) (%)", 0.0, 30.0, 12.0)
            estimated_exit_value = st.number_input(
                "Valeur de sortie estimée (vente ou capitalisation des loyers) (€)",
                min_value=0.0,
                value=1_000_000.0,
                step=10_000.0,
            )
            proforma_submitted = st.form_submit_button("Calculer le pro forma")

        if proforma_submitted:
            try:
                response = requests.post(
                    f"{ORCHESTRATOR_URL}/land/proforma",
                    json={
                        "land_cost": land_cost,
                        "construction_cost_per_m2": construction_cost_per_m2,
                        "surface_to_build_m2": surface_to_build_m2,
                        "soft_costs_pct": soft_costs_pct,
                        "estimated_exit_value": estimated_exit_value,
                    },
                    timeout=30,
                )
                response.raise_for_status()
                st.session_state["land_proforma"] = response.json()
            except requests.RequestException as exc:
                st.error(f"Erreur de calcul du pro forma : {exc}")

        proforma = st.session_state.get("land_proforma")
        if proforma:
            c1, c2, c3 = st.columns(3)
            c1.metric("Coût total du projet", f"{proforma['total_project_cost']:,.0f} €".replace(",", " "))
            c2.metric("Marge", f"{proforma['margin']:,.0f} €".replace(",", " "))
            c3.metric("Marge %", f"{proforma['margin_pct']:.1f}%")
            if proforma["margin"] < 0:
                st.warning("Le projet est déficitaire avec ces hypothèses.")

        st.subheader("3. Agent de conception — étude de volume")
        st.caption(
            "Décris ton projet en discutant avec l'agent, ou pars d'un modèle prêt à l'emploi. "
            "Une fois qu'il a assez d'informations (type de bâtiment, dimensions, étages, "
            "toiture, style), il propose un volume 3D indicatif."
        )

        st.session_state.setdefault("land_chat_history", [])
        st.session_state.setdefault("land_brief", None)
        st.session_state.setdefault("land_suggestions", [])

        st.write("**Démarrer avec un modèle prêt à l'emploi :**")
        tpl_cols = st.columns(len(DESIGN_TEMPLATES))
        for col, tpl in zip(tpl_cols, DESIGN_TEMPLATES):
            if col.button(tpl["label"], key=f"tpl_{tpl['label']}", use_container_width=True):
                _apply_design_template(tpl["brief"])
                st.rerun()

        for msg in st.session_state["land_chat_history"]:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        feasibility_context = (
            f"Emprise au sol constructible {feasibility['buildable_footprint_m2']} m2, "
            f"{feasibility['max_floors']} etage(s) maximum, hauteur d'etage {floor_height_m} m."
        )

        if st.session_state["land_suggestions"]:
            sugg_cols = st.columns(len(st.session_state["land_suggestions"]))
            for col, sugg in zip(sugg_cols, st.session_state["land_suggestions"]):
                if col.button(sugg, key=f"sugg_{sugg}", use_container_width=True):
                    _send_design_chat(sugg, feasibility_context)
                    st.rerun()

        user_msg = st.chat_input("Décris ton projet de construction...")
        if user_msg:
            _send_design_chat(user_msg, feasibility_context)
            st.rerun()

        brief = st.session_state.get("land_brief")
        if brief:
            st.subheader("4. Façade photoréaliste — vue à 360°")
            st.caption(
                f"{brief['building_type']} — style {brief.get('architectural_style', 'contemporain')} — "
                f"{brief['footprint_length_m']}m × {brief['footprint_width_m']}m — "
                f"{brief['floors']} étage(s) — toit {brief['roof_type']}"
            )

            st.write("**Retouches rapides :**")
            tc1, tc2, tc3, tc4, tc5 = st.columns(5)
            if tc1.button("➕ Étage", use_container_width=True):
                max_floors = feasibility.get("max_floors", brief["floors"] + 1)
                brief["floors"] = min(brief["floors"] + 1, max_floors)
                st.session_state["land_brief"] = brief
                st.session_state.pop("land_facade_360", None)
                st.rerun()
            if tc2.button("➖ Étage", use_container_width=True, disabled=brief["floors"] <= 1):
                brief["floors"] = max(1, brief["floors"] - 1)
                st.session_state["land_brief"] = brief
                st.session_state.pop("land_facade_360", None)
                st.rerun()
            if tc3.button("🔄 Style suivant", use_container_width=True):
                current = brief.get("architectural_style", "contemporain")
                idx = ARCHITECTURAL_STYLES.index(current) if current in ARCHITECTURAL_STYLES else -1
                brief["architectural_style"] = ARCHITECTURAL_STYLES[(idx + 1) % len(ARCHITECTURAL_STYLES)]
                st.session_state["land_brief"] = brief
                st.session_state.pop("land_facade_360", None)
                st.rerun()
            if tc4.button("🏠 Toit suivant", use_container_width=True):
                current = brief.get("roof_type", "plat")
                idx = ROOF_TYPES.index(current) if current in ROOF_TYPES else -1
                brief["roof_type"] = ROOF_TYPES[(idx + 1) % len(ROOF_TYPES)]
                st.session_state["land_brief"] = brief
                st.session_state.pop("land_facade_360", None)
                st.rerun()
            if tc5.button("🎲 Surprends-moi", use_container_width=True):
                max_floors = feasibility.get("max_floors", brief["floors"])
                brief["floors"] = random.randint(1, max(1, max_floors))
                brief["architectural_style"] = random.choice(ARCHITECTURAL_STYLES)
                brief["roof_type"] = random.choice(ROOF_TYPES)
                st.session_state["land_brief"] = brief
                st.session_state.pop("land_facade_360", None)
                st.rerun()

            if st.button("🔄 Générer la vue 360°", use_container_width=True):
                _generate_facade_360(brief)

            facade_360 = st.session_state.get("land_facade_360")
            if facade_360 and facade_360.get("images"):
                components.html(render_facade_360_html(facade_360["images"]), height=580)
                st.caption(
                    "8 vues photoréalistes générées par IA (SDXL) autour du bâtiment, avec un point de départ "
                    "aléatoire partagé pour rester visuellement cohérentes entre elles — pas un modèle 3D mesurable, "
                    "une série de photos. Chaque changement de style/étage/toit ci-dessus nécessite de régénérer la vue."
                )
            elif facade_360 and facade_360.get("error"):
                st.warning(f"Génération de la vue 360° impossible : {facade_360['error']}")
            else:
                st.info("Clique sur « Générer la vue 360° » pour voir la façade sous tous les angles.")

            st.subheader("5. Intérieur & jardin — rendu IA photoréaliste")
            st.caption(
                "Génère un aperçu photoréaliste de chaque pièce ou du jardin, dans le style architectural "
                "choisi, via Stable Diffusion XL auto-hébergé sur GPU local (1024×1024). Ce sont des images "
                "2D indicatives, pas un plan mesurable — voir la maquette 3D pour un volume mesurable."
                + (
                    " Ces rendus reprennent le point de départ visuel de la vue 360° générée en section 4 "
                    "pour rester cohérents avec la façade."
                    if st.session_state.get("land_facade_360", {}).get("seed")
                    else " Génère d'abord la vue 360° en section 4 pour des pièces visuellement cohérentes avec la façade."
                )
            )
            st.session_state.setdefault("interior_renders", {})
            room_types = interior_room_types(brief.get("building_type", ""))
            room_cols = st.columns(len(room_types))
            for col, (room_key, room_label) in zip(room_cols, room_types):
                if col.button(room_label, key=f"interior_{room_key}", use_container_width=True):
                    _generate_interior_render(room_key, brief)

            for room_key, room_label in room_types:
                render = st.session_state["interior_renders"].get(room_key)
                if not render:
                    continue
                if render.get("image_url"):
                    st.image(render["image_url"], caption=room_label, use_container_width=True)
                elif render.get("error"):
                    st.warning(f"{room_label} : {render['error']}")

            if st.button("Recommencer la conception"):
                st.session_state["land_chat_history"] = []
                st.session_state["land_brief"] = None
                st.session_state["land_suggestions"] = []
                st.session_state["interior_renders"] = {}
                st.session_state.pop("land_facade_360", None)
                st.rerun()


st.title("DealPilot AI")
st.caption("Système intelligent d'acquisition, de promotion et de construction immobilière — France")

role = st.radio(
    "Je suis :",
    options=["investisseur", "promoteur", "citoyen"],
    format_func=lambda r: {"investisseur": "🏢 Investisseur", "promoteur": "🏗️ Promoteur", "citoyen": "🏠 Citoyen"}[r],
    horizontal=True,
)

if role == "investisseur":
    render_investor_flow()
else:
    render_promoter_flow(role)
