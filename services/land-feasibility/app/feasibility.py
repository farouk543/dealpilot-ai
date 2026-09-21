import math

from dealpilot_shared import LandConstraints, LandFeasibility

from .administrative import build_administrative_checklist
from .geocoding import geocode_address
from .zoning import fetch_real_zoning

_BASE_NOTE = (
    "Calcul a partir des contraintes fournies par l'utilisateur (emprise au sol max, "
    "hauteur max, hauteur d'etage). A verifier aupres du service urbanisme de la commune "
    "avant tout engagement."
)


def compute_feasibility(constraints: LandConstraints) -> LandFeasibility:
    buildable_footprint = constraints.surface_terrain_m2 * constraints.emprise_au_sol_max_pct / 100
    max_floors = max(1, math.floor(constraints.hauteur_max_m / constraints.floor_height_m))
    max_buildable_surface = buildable_footprint * max_floors

    real_zoning = None
    checklist = []
    note = _BASE_NOTE
    if constraints.address:
        coords = geocode_address(constraints.address)
        if coords is not None:
            real_zoning = fetch_real_zoning(*coords)
        if real_zoning is not None:
            note += (
                f" Zone officielle trouvee au Geoportail de l'Urbanisme : {real_zoning.zone_code} "
                "(voir ci-dessous) — fournie a titre informatif, le systeme n'extrait pas encore "
                "automatiquement les regles chiffrees du reglement PLU associe."
            )
            checklist = build_administrative_checklist(real_zoning.zone_type, max_buildable_surface)
        else:
            note += (
                " Zone officielle non trouvee pour cette adresse au Geoportail de l'Urbanisme "
                "(parcelle non couverte, adresse imprecise, ou commune sous RNU)."
            )

    return LandFeasibility(
        surface_terrain_m2=constraints.surface_terrain_m2,
        buildable_footprint_m2=round(buildable_footprint, 1),
        max_floors=max_floors,
        max_buildable_surface_m2=round(max_buildable_surface, 1),
        assumptions_note=note,
        real_zoning=real_zoning,
        administrative_checklist=checklist,
    )
