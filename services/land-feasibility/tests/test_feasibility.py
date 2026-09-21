from dealpilot_shared import LandConstraints, RealZoning

from app import feasibility as feasibility_module
from app.feasibility import compute_feasibility


def test_buildable_footprint_hand_computed():
    constraints = LandConstraints(surface_terrain_m2=500, emprise_au_sol_max_pct=40, hauteur_max_m=9, floor_height_m=3)
    result = compute_feasibility(constraints)
    assert result.buildable_footprint_m2 == 200.0  # 500 * 0.40
    assert result.max_floors == 3  # 9 / 3
    assert result.max_buildable_surface_m2 == 600.0  # 200 * 3


def test_max_floors_rounds_down():
    constraints = LandConstraints(surface_terrain_m2=300, emprise_au_sol_max_pct=50, hauteur_max_m=8, floor_height_m=3)
    result = compute_feasibility(constraints)
    assert result.max_floors == 2  # floor(8/3) = 2, not 2.67


def test_max_floors_never_zero():
    constraints = LandConstraints(surface_terrain_m2=200, emprise_au_sol_max_pct=50, hauteur_max_m=2, floor_height_m=3)
    result = compute_feasibility(constraints)
    assert result.max_floors == 1


def test_assumptions_note_present():
    constraints = LandConstraints(surface_terrain_m2=500, emprise_au_sol_max_pct=40, hauteur_max_m=9, floor_height_m=3)
    result = compute_feasibility(constraints)
    assert "urbanisme" in result.assumptions_note
    assert result.real_zoning is None


def test_no_zoning_lookup_without_address():
    constraints = LandConstraints(surface_terrain_m2=500, emprise_au_sol_max_pct=40, hauteur_max_m=9, floor_height_m=3)
    result = compute_feasibility(constraints)
    assert result.real_zoning is None


def test_real_zoning_attached_when_address_resolves(monkeypatch):
    monkeypatch.setattr(feasibility_module, "geocode_address", lambda address: (45.764, 4.8357))
    monkeypatch.setattr(
        feasibility_module,
        "fetch_real_zoning",
        lambda lat, lon: RealZoning(
            zone_code="UCe1b", zone_type="U", description="Tissu urbain dense", plu_reference="200046977_PLUI"
        ),
    )
    constraints = LandConstraints(
        surface_terrain_m2=500, emprise_au_sol_max_pct=40, hauteur_max_m=9, floor_height_m=3,
        address="1 place Bellecour, Lyon",
    )
    result = compute_feasibility(constraints)
    assert result.real_zoning is not None
    assert result.real_zoning.zone_code == "UCe1b"
    assert "UCe1b" in result.assumptions_note


def test_zoning_lookup_failure_is_graceful(monkeypatch):
    monkeypatch.setattr(feasibility_module, "geocode_address", lambda address: None)
    constraints = LandConstraints(
        surface_terrain_m2=500, emprise_au_sol_max_pct=40, hauteur_max_m=9, floor_height_m=3,
        address="adresse introuvable, nulle part",
    )
    result = compute_feasibility(constraints)
    assert result.real_zoning is None
    assert "non trouvee" in result.assumptions_note
    assert result.administrative_checklist == []


def test_checklist_warns_on_agricultural_zone(monkeypatch):
    monkeypatch.setattr(feasibility_module, "geocode_address", lambda address: (45.0, 4.0))
    monkeypatch.setattr(
        feasibility_module,
        "fetch_real_zoning",
        lambda lat, lon: RealZoning(zone_code="A1", zone_type="A", description="Zone agricole"),
    )
    constraints = LandConstraints(
        surface_terrain_m2=500, emprise_au_sol_max_pct=40, hauteur_max_m=9, floor_height_m=3, address="ferme, Lyon"
    )
    result = compute_feasibility(constraints)
    assert any("restreinte" in step.label for step in result.administrative_checklist)


def test_checklist_uses_permis_de_construire_for_large_projects(monkeypatch):
    monkeypatch.setattr(feasibility_module, "geocode_address", lambda address: (45.0, 4.0))
    monkeypatch.setattr(
        feasibility_module,
        "fetch_real_zoning",
        lambda lat, lon: RealZoning(zone_code="UB", zone_type="U", description="Zone urbaine"),
    )
    constraints = LandConstraints(
        surface_terrain_m2=500, emprise_au_sol_max_pct=40, hauteur_max_m=9, floor_height_m=3, address="1 rue X, Lyon"
    )
    result = compute_feasibility(constraints)
    labels = [step.label for step in result.administrative_checklist]
    assert any("Permis de construire" in label for label in labels)
