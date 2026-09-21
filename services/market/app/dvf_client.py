import csv
import os
import statistics
from pathlib import Path

import httpx

from dealpilot_shared.http_retry import with_retry

CACHE_ROOT = Path(os.environ.get("DVF_CACHE_ROOT", "/data/dvf_cache"))
_BASE_URL = "https://files.data.gouv.fr/geo-dvf/latest/csv"

# Paris/Lyon/Marseille only publish DVF data at the arrondissement level,
# never under their aggregate INSEE code.
_PLM_ARRONDISSEMENTS = {
    "75056": [f"751{n:02d}" for n in range(1, 21)],
    "69123": [f"69{n}" for n in range(381, 390)],
    "13055": [f"132{n:02d}" for n in range(1, 17)],
}

_VALID_TYPES = {"Appartement", "Maison"}
_MIN_PRICE_PER_M2 = 500.0
_MAX_PRICE_PER_M2 = 15000.0


def expand_commune_code(insee_code: str) -> list[str]:
    return _PLM_ARRONDISSEMENTS.get(insee_code, [insee_code])


def _fetch_commune_csv(year: int, insee_code: str) -> list[dict]:
    dept = insee_code[:2]
    cache_path = CACHE_ROOT / str(year) / f"{insee_code}.csv"

    if not cache_path.exists():
        url = f"{_BASE_URL}/{year}/communes/{dept}/{insee_code}.csv"
        try:
            response = with_retry(lambda: httpx.get(url, timeout=30.0, follow_redirects=True))
        except Exception:
            return []
        if response.status_code != 200:
            return []
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(response.content)

    with cache_path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fetch_transactions(insee_codes: list[str], years: list[int]) -> list[dict]:
    rows = []
    for code in insee_codes:
        for year in years:
            rows.extend(_fetch_commune_csv(year, code))
    return rows


def compute_comparables(rows: list[dict], subject_surface_m2: float) -> dict:
    retained = []
    rejected_out_of_range = 0

    for row in rows:
        if row.get("nature_mutation") != "Vente" or row.get("type_local") not in _VALID_TYPES:
            continue
        try:
            surface = float(row["surface_reelle_bati"])
            price = float(row["valeur_fonciere"])
        except (TypeError, ValueError):
            continue
        if surface <= 0 or price <= 0:
            continue

        price_per_m2 = price / surface
        if not (_MIN_PRICE_PER_M2 <= price_per_m2 <= _MAX_PRICE_PER_M2):
            rejected_out_of_range += 1
            continue

        retained.append(
            {
                "date": row.get("date_mutation"),
                "type_local": row.get("type_local"),
                "surface_m2": surface,
                "price": price,
                "price_per_m2": round(price_per_m2, 2),
                "commune": row.get("nom_commune"),
                "address": f"{row.get('adresse_numero', '')} {row.get('adresse_nom_voie', '')}".strip(),
            }
        )

    if not retained:
        return {
            "comparables_count": 0,
            "rejected_out_of_range": rejected_out_of_range,
            "price_per_m2": None,
            "estimated_value_range": None,
            "sample": [],
        }

    prices_per_m2 = sorted(c["price_per_m2"] for c in retained)
    quantiles = statistics.quantiles(prices_per_m2, n=4) if len(prices_per_m2) >= 4 else None
    p25 = quantiles[0] if quantiles else prices_per_m2[0]
    median = statistics.median(prices_per_m2)
    p75 = quantiles[2] if quantiles else prices_per_m2[-1]

    sample = sorted(retained, key=lambda c: c["date"] or "", reverse=True)[:10]

    return {
        "comparables_count": len(retained),
        "rejected_out_of_range": rejected_out_of_range,
        "price_per_m2": {"p25": round(p25, 2), "median": round(median, 2), "p75": round(p75, 2)},
        "estimated_value_range": {
            "low": round(p25 * subject_surface_m2, 2),
            "median": round(median * subject_surface_m2, 2),
            "high": round(p75 * subject_surface_m2, 2),
        },
        "sample": sample,
    }
