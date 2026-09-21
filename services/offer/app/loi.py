from dealpilot_shared import PropertyRecord


def render_loi(property: PropertyRecord, target_price: float | None, conditions: list[str]) -> str:
    conditions_text = "\n".join(f"- {c}" for c in conditions)
    price_text = f"{target_price:,.0f} EUR".replace(",", " ") if target_price is not None else "[a determiner]"

    return f"""LETTRE D'INTENTION NON CONTRAIGNANTE (PROJET — A VALIDER PAR L'UTILISATEUR AVANT ENVOI)

Bien : {property.property_type} — {property.location}
Prix propose (indicatif) : {price_text}

Cette lettre exprime un interet non contraignant pour l'acquisition du bien ci-dessus,
sous reserve des conditions suivantes et d'une due diligence complete :

{conditions_text}

Ce document est un projet automatiquement genere. Il ne constitue ni une offre ferme,
ni un engagement contractuel, et doit etre revu et valide par l'investisseur (et, le cas
echeant, son conseil) avant toute transmission au vendeur.
"""
