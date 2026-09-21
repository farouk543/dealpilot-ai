import httpx

from dealpilot_shared.http_retry import with_retry

_GEO_API_BASE = "https://geo.api.gouv.fr/communes"


def resolve_commune_code(location: str) -> str | None:
    try:
        response = with_retry(
            lambda: httpx.get(
                _GEO_API_BASE,
                params={
                    "nom": location,
                    "fields": "nom,code,codeDepartement,population",
                    "boost": "population",
                    "limit": 5,
                },
                timeout=15.0,
            )
        )
        response.raise_for_status()
        results = response.json()
    except Exception:
        return None

    if not results:
        return None
    return results[0]["code"]
