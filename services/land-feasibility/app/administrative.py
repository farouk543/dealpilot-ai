from dealpilot_shared import AdministrativeStep

# General, informational guidance only — derived from the zone's broad legal
# category (U/AU/A/N, per the French urbanisme code) and rough project size.
# Real requirements also depend on the commune's own PLU rules, protected-site
# status, surface built, etc., which this system does not parse (see
# LandConstraints docstring). Always says so explicitly in every step.

_COMMON_FIRST_STEP = AdministrativeStep(
    label="Certificat d'urbanisme (recommandé avant tout dépôt)",
    description=(
        "Demander un certificat d'urbanisme (CUa ou CUb) aupres de la mairie pour confirmer "
        "la constructibilite reelle et les servitudes applicables a la parcelle, avant d'engager "
        "des frais de conception."
    ),
)


def build_administrative_checklist(zone_type: str, buildable_surface_m2: float) -> list[AdministrativeStep]:
    steps = [_COMMON_FIRST_STEP]
    zone = (zone_type or "?").upper()

    if zone in ("A", "N"):
        steps.append(
            AdministrativeStep(
                label="⚠️ Constructibilité très restreinte (zone agricole/naturelle)",
                description=(
                    "En zone A (agricole) ou N (naturelle), la construction neuve est en principe "
                    "interdite sauf exceptions strictes (exploitation agricole, extension limitee "
                    "d'existant...). Verifier l'eligibilite du projet aupres du service urbanisme "
                    "avant tout investissement en conception — un refus est probable hors cas prevu par le PLU."
                ),
            )
        )
        return steps

    # Zone U (urbaine) or AU (à urbaniser) — the standard buildable case.
    if buildable_surface_m2 <= 20:
        steps.append(
            AdministrativeStep(
                label="Déclaration préalable de travaux",
                description=(
                    "Pour une emprise au sol ou surface de plancher creee entre 5 et 20 m² "
                    "(jusqu'a 40 m² en zone urbaine couverte par un PLU), une declaration prealable "
                    "suffit generalement au lieu d'un permis de construire complet."
                ),
            )
        )
    else:
        steps.append(
            AdministrativeStep(
                label="Permis de construire",
                description=(
                    "Au-dela des seuils de la declaration prealable (projet de promotion typique), "
                    "un permis de construire complet est requis : plans, notice, insertion paysagere, "
                    "delai d'instruction generalement de 2 a 3 mois hors majoration."
                ),
            )
        )

    if zone == "AU":
        steps.append(
            AdministrativeStep(
                label="Vérifier l'ouverture effective de la zone AU",
                description=(
                    "Les zones AU (a urbaniser) sont parfois soumises a une ouverture progressive "
                    "(orientations d'amenagement, modification du PLU requise avant constructibilite "
                    "effective). Confirmer que la zone est bien ouverte a l'urbanisation."
                ),
            )
        )

    steps.append(
        AdministrativeStep(
            label="Étude d'impact / raccordements",
            description=(
                "Selon la taille du projet : etude d'impact environnemental eventuelle, raccordements "
                "reseaux (eau, electricite, assainissement) a verifier aupres des concessionnaires locaux."
            ),
        )
    )
    return steps
