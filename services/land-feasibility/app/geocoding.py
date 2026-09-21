import httpx

from dealpilot_shared.http_retry import with_retry

_BAN_URL = "https://api-adresse.data.gouv.fr/search/"


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
