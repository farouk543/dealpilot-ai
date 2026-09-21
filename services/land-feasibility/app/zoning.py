import json

import httpx

from dealpilot_shared import RealZoning
from dealpilot_shared.http_retry import with_retry

# Geoportail de l'Urbanisme registry, served by IGN's Apicarto API — official,
# free, no key required. Gives the real PLU zone for a parcel, but not
# machine-readable numeric buildability rules (see LandConstraints docstring).
_GPU_ZONE_URBA_URL = "https://apicarto.ign.fr/api/gpu/zone-urba"


def fetch_real_zoning(lat: float, lon: float) -> RealZoning | None:
    geometry = json.dumps({"type": "Point", "coordinates": [lon, lat]})
    try:
        response = with_retry(lambda: httpx.get(_GPU_ZONE_URBA_URL, params={"geom": geometry}, timeout=15.0))
        response.raise_for_status()
        features = response.json().get("features", [])
    except Exception:
        return None

    if not features:
        return None

    props = features[0].get("properties", {})
    zone_code = props.get("libelle")
    if not zone_code:
        return None

    return RealZoning(
        zone_code=zone_code,
        zone_type=props.get("typezone") or "?",
        description=props.get("libelong") or "Pas de description disponible.",
        plu_reference=props.get("idurba") or props.get("nomfic"),
    )
