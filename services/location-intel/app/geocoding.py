import httpx

from dealpilot_shared.http_retry import with_retry

_BAN_URL = "https://api-adresse.data.gouv.fr/search/"
_GEO_COMMUNES_URL = "https://geo.api.gouv.fr/communes"


def geocode_address(address: str) -> tuple[float, float] | None:
    """Precise geocoding of a street address via the French national address base (BAN)."""
    try:
        response = with_retry(lambda: httpx.get(_BAN_URL, params={"q": address, "limit": 1}, timeout=15.0))
        response.raise_for_status()
        features = response.json().get("features", [])
    except Exception:
        return None

    if not features:
        return None
    lon, lat = features[0]["geometry"]["coordinates"]
    return lat, lon


def geocode_city(city: str) -> tuple[float, float] | None:
    """Fallback: city/commune centroid via geo.api.gouv.fr when no precise address is given."""
    try:
        response = with_retry(
            lambda: httpx.get(
                _GEO_COMMUNES_URL,
                params={"nom": city, "fields": "centre,population", "boost": "population", "limit": 1},
                timeout=15.0,
            )
        )
        response.raise_for_status()
        results = response.json()
    except Exception:
        return None

    if not results or "centre" not in results[0]:
        return None
    lon, lat = results[0]["centre"]["coordinates"]
    return lat, lon


def geocode(address: str | None, city: str) -> tuple[float, float] | None:
    if address:
        coords = geocode_address(address)
        if coords is not None:
            return coords
    return geocode_city(city)
