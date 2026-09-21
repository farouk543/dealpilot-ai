import os

from fastapi import FastAPI
from pydantic import BaseModel

from dealpilot_shared import ExtractedFact, Provenance, SourceType
from dealpilot_shared.logging_utils import CorrelationIdMiddleware, configure_logging

from .commune_resolver import resolve_commune_code
from .dvf_client import compute_comparables, expand_commune_code, fetch_transactions

configure_logging("market")

app = FastAPI(title="DealPilot AI — Market")
app.add_middleware(CorrelationIdMiddleware)

_YEARS = [int(y) for y in os.environ.get("DVF_YEARS", "2023,2022,2021").split(",")]

_LIMITATION_NOTE = (
    "Comparables issus de ventes unitaires (appartements/maisons) DVF, "
    "extrapoles au prorata de la surface totale du bien : n'equivaut pas a "
    "une vente d'immeuble entier et ne tient pas compte d'une decote/surcote "
    "liee a la vente en bloc."
)


class ComparablesRequest(BaseModel):
    deal_id: str
    location: str
    surface_m2: float


@app.post("/comparables")
def comparables(payload: ComparablesRequest) -> dict:
    base_code = resolve_commune_code(payload.location)
    if base_code is None:
        fact = ExtractedFact(
            field_name="market_error",
            value=f"commune introuvable pour la localisation '{payload.location}'",
            provenance=Provenance(source_type=SourceType.EXTERNAL_SOURCE, reference="geo.api.gouv.fr"),
        )
        return {"document_facts": [fact.model_dump(mode="json")]}

    insee_codes = expand_commune_code(base_code)
    rows = fetch_transactions(insee_codes, _YEARS)
    result = compute_comparables(rows, payload.surface_m2)

    reference = f"DVF {','.join(str(y) for y in _YEARS)} / commune(s) {','.join(insee_codes)}"
    facts: list[ExtractedFact] = []

    if result["comparables_count"] == 0:
        facts.append(
            ExtractedFact(
                field_name="market_error",
                value="aucune transaction comparable trouvee dans les donnees DVF disponibles",
                provenance=Provenance(source_type=SourceType.EXTERNAL_SOURCE, reference=reference),
            )
        )
        return {"document_facts": [f.model_dump(mode="json") for f in facts]}

    provenance = Provenance(
        source_type=SourceType.EXTERNAL_SOURCE,
        reference=reference,
        note=f"{result['comparables_count']} comparables retenus, {result['rejected_out_of_range']} ecartes (prix/m2 hors bornes plausibles)",
    )

    facts.append(
        ExtractedFact(
            field_name="market_price_per_m2_median",
            value=str(result["price_per_m2"]["median"]),
            provenance=provenance,
        )
    )
    facts.append(
        ExtractedFact(
            field_name="market_value_low",
            value=str(result["estimated_value_range"]["low"]),
            provenance=provenance,
        )
    )
    facts.append(
        ExtractedFact(
            field_name="market_value_median",
            value=str(result["estimated_value_range"]["median"]),
            provenance=provenance,
        )
    )
    facts.append(
        ExtractedFact(
            field_name="market_value_high",
            value=str(result["estimated_value_range"]["high"]),
            provenance=provenance,
        )
    )
    facts.append(
        ExtractedFact(
            field_name="market_rationale",
            value=_LIMITATION_NOTE,
            provenance=Provenance(source_type=SourceType.EXTERNAL_SOURCE, reference=reference),
        )
    )

    return {"document_facts": [f.model_dump(mode="json") for f in facts], "detail": result}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
