import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _fmt_money(value) -> str:
    if value is None:
        return "—"
    return f"{value:,.0f} €".replace(",", " ")


def _fmt_pct(value) -> str:
    if value is None:
        return "—"
    return f"{value:.2f} %"


def build_pdf(deal: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("DealPilot AI — Dossier d'analyse", styles["Title"]))
    story.append(Paragraph(f"Dossier {deal.get('deal_id', '')}", styles["Normal"]))
    story.append(Spacer(1, 14))

    prop = deal.get("property") or {}
    if prop:
        story.append(Paragraph("Bien immobilier", styles["Heading2"]))
        address = f", {prop['address']}" if prop.get("address") else ""
        story.append(Paragraph(f"{prop.get('property_type', '')} — {prop.get('location', '')}{address}", styles["Normal"]))
        story.append(Spacer(1, 12))

    underwriting = deal.get("underwriting")
    if underwriting and underwriting.get("scenarios"):
        story.append(Paragraph("Souscription financière (3 scénarios)", styles["Heading2"]))
        rows = [["Scénario", "NOI", "Cap rate", "Cash-flow", "Cash-on-cash", "DSCR"]]
        for s in underwriting["scenarios"]:
            dscr = s.get("dscr")
            dscr_text = f"{dscr:.2f}" if isinstance(dscr, (int, float)) else str(dscr)
            rows.append(
                [
                    s["name"],
                    _fmt_money(s.get("noi")),
                    _fmt_pct(s.get("cap_rate_pct")),
                    _fmt_money(s.get("cash_flow_before_tax")),
                    _fmt_pct(s.get("cash_on_cash_pct")),
                    dscr_text,
                ]
            )
        table = Table(rows, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2f5c3a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 14))

    risk_register = deal.get("risk_register")
    if risk_register and risk_register.get("risks"):
        story.append(Paragraph("Registre des risques", styles["Heading2"]))
        for r in risk_register["risks"]:
            story.append(
                Paragraph(
                    f"<b>[{r['severity']}] {r['title']}</b> — {r['impact']} (action: {r['next_action']})",
                    styles["Normal"],
                )
            )
        story.append(Spacer(1, 14))

    offer = deal.get("offer")
    if offer:
        story.append(Paragraph("Stratégie d'offre", styles["Heading2"]))
        story.append(
            Paragraph(
                f"Prix cible : {_fmt_money(offer.get('target_price'))} — "
                f"Prix maximum : {_fmt_money(offer.get('max_price'))} — "
                f"Plafond scénario de stress : {_fmt_money(offer.get('stress_cap_price'))}",
                styles["Normal"],
            )
        )
        story.append(Paragraph(offer.get("rationale", ""), styles["Normal"]))
        story.append(Spacer(1, 14))

    dd = deal.get("due_diligence")
    if dd:
        story.append(Paragraph("Due diligence", styles["Heading2"]))
        if dd.get("decision_ready"):
            story.append(Paragraph("Aucun risque élevé non résolu — dossier prêt pour une décision.", styles["Normal"]))
        else:
            story.append(
                Paragraph(
                    f"{dd.get('unresolved_high_risk_tasks', 0)} tâche(s) liée(s) à un risque élevé "
                    "encore ouverte(s) — décision d'achat non recommandée en l'état.",
                    styles["Normal"],
                )
            )
        story.append(Spacer(1, 14))

    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            "Document généré automatiquement par DealPilot AI — étude indicative basée sur les données "
            "fournies et des données publiques, ne constitue pas un conseil financier, juridique ou "
            "d'investissement personnalisé.",
            styles["Italic"],
        )
    )

    doc.build(story)
    return buffer.getvalue()
