import urllib.parse

import httpx

_OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
_USER_AGENT = "DealPilotAI/0.1 (real-estate-analysis)"

# Exact-match filters only: Overpass QL regex filters (e.g. amenity~"a|b|c") are
# far slower server-side and were observed to time out; a union of cheap exact
# filters for the same categories returns in a few seconds instead.
_AMENITY_TAGS = ["restaurant", "cafe", "fast_food", "pharmacy", "school", "bank"]


def _build_query(lat: float, lon: float, radius_m: int) -> str:
    around = f"(around:{radius_m},{lat},{lon})"
    lines = [f'node["shop"]{around};']
    lines += [f'node["amenity"="{tag}"]{around};' for tag in _AMENITY_TAGS]
    lines.append(f'node["public_transport"="stop_position"]{around};')
    return "[out:json][timeout:20];(" + "".join(lines) + ");out tags;"


def fetch_pois(lat: float, lon: float, radius_m: int = 400) -> list[dict] | None:
    query = _build_query(lat, lon, radius_m)
    body = urllib.parse.urlencode({"data": query}).encode()
    headers = {"User-Agent": _USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"}

    for endpoint in _OVERPASS_ENDPOINTS:
        try:
            response = httpx.post(endpoint, content=body, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json().get("elements", [])
        except Exception:
            continue
    return None


def aggregate_categories(elements: list[dict]) -> dict[str, int]:
    counts = {
        "commerces": 0,
        "restauration": 0,
        "sante": 0,
        "education": 0,
        "services_bancaires": 0,
        "transport": 0,
    }
    for element in elements:
        tags = element.get("tags", {})
        if tags.get("shop"):
            counts["commerces"] += 1
        elif tags.get("amenity") in {"restaurant", "cafe", "fast_food"}:
            counts["restauration"] += 1
        elif tags.get("amenity") == "pharmacy":
            counts["sante"] += 1
        elif tags.get("amenity") == "school":
            counts["education"] += 1
        elif tags.get("amenity") == "bank":
            counts["services_bancaires"] += 1
        elif tags.get("public_transport"):
            counts["transport"] += 1
    return counts


def vibrancy_index(counts: dict[str, int]) -> int:
    """Indicative 0-100 score, not a validated metric — weights favor walkable,
    commerce-dense, transit-served areas."""
    raw = (
        counts["commerces"] * 2
        + counts["restauration"] * 3
        + counts["transport"] * 6
        + counts["sante"] * 4
        + counts["education"] * 3
        + counts["services_bancaires"] * 3
    )
    return min(100, raw)
