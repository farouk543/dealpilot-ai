from enum import Enum

from pydantic import BaseModel


class UserRole(str, Enum):
    INVESTISSEUR = "investisseur"
    PROMOTEUR = "promoteur"
    CITOYEN = "citoyen"


class LandConstraints(BaseModel):
    """User-provided zoning constraints (emprise au sol/hauteur max) remain the
    actual calculation inputs — the French PLU registry (Geoportail de
    l'Urbanisme, queried via IGN's Apicarto API) does not expose machine-
    readable numeric buildability rules nationwide, only the zone identity
    and its regulation document. When `address` is given, that real zone
    identity is looked up and shown alongside the user's figures as
    informational context, not as a replacement for them."""

    surface_terrain_m2: float
    emprise_au_sol_max_pct: float = 50.0
    hauteur_max_m: float = 9.0
    floor_height_m: float = 3.0
    address: str | None = None


class RealZoning(BaseModel):
    """Actual PLU zone for the parcel, from the official Geoportail de
    l'Urbanisme registry (via IGN's Apicarto API) — zone identity only, not
    parsed numeric rules (see LandConstraints docstring)."""

    zone_code: str
    zone_type: str
    description: str
    plu_reference: str | None = None


class AdministrativeStep(BaseModel):
    """A typical administrative step for the detected zone type — general,
    informational guidance derived only from the zone's broad category (U/AU/A/N)
    and project size, never a substitute for confirming the actual requirement
    with the commune's service urbanisme."""

    label: str
    description: str


class LandFeasibility(BaseModel):
    surface_terrain_m2: float
    buildable_footprint_m2: float
    max_floors: int
    max_buildable_surface_m2: float
    assumptions_note: str
    real_zoning: RealZoning | None = None
    administrative_checklist: list[AdministrativeStep] = []


class DevelopmentProForma(BaseModel):
    land_cost: float
    construction_cost_per_m2: float
    surface_to_build_m2: float
    construction_cost_total: float
    soft_costs_pct: float
    soft_costs_total: float
    total_project_cost: float
    estimated_exit_value: float
    margin: float
    margin_pct: float


class BuildingDesignBrief(BaseModel):
    footprint_length_m: float
    footprint_width_m: float
    floors: int
    floor_height_m: float = 3.0
    roof_type: str = "plat"
    building_type: str = "residentiel"
    # Real, documented architectural movements — not a free-form style, so the
    # 3D renderer can apply their actual signature features (ribbon windows +
    # pilotis for moderniste, wrought-iron balconies for haussmannien, etc.)
    # rather than an arbitrary look.
    architectural_style: str = "contemporain"
