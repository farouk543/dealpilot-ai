from fastapi import FastAPI
from pydantic import BaseModel

from dealpilot_shared import ExtractedFact, Provenance, SourceType
from dealpilot_shared.logging_utils import CorrelationIdMiddleware, configure_logging

from .analysis import analyze_location
from .geocoding import geocode
from .osm import aggregate_categories, fetch_pois, vibrancy_index

configure_logging("location-intel")

app = FastAPI(title="DealPilot AI — Location Intelligence")
app.add_middleware(CorrelationIdMiddleware)

_RADIUS_M = 400


class LocationRequest(BaseModel):
    deal_id: str
    property_type: str
    location: str
    address: str | None = None


@app.post("/analyze")
def analyze(payload: LocationRequest) -> dict:
    facts: list[ExtractedFact] = []

    coords = geocode(payload.address, payload.location)
    if coords is None:
        facts.append(
            ExtractedFact(
                field_name="location_error",
                value=f"geocodage impossible pour '{payload.address or payload.location}'",
                provenance=Provenance(source_type=SourceType.EXTERNAL_SOURCE, reference="BAN/geo.api.gouv.fr"),
            )
        )
        return {"document_facts": [f.model_dump(mode="json") for f in facts]}

    lat, lon = coords
    facts.append(
        ExtractedFact(
            field_name="location_latitude",
            value=str(lat),
            provenance=Provenance(source_type=SourceType.EXTERNAL_SOURCE, reference="BAN/geo.api.gouv.fr"),
        )
    )
    facts.append(
        ExtractedFact(
            field_name="location_longitude",
            value=str(lon),
            provenance=Provenance(source_type=SourceType.EXTERNAL_SOURCE, reference="BAN/geo.api.gouv.fr"),
        )
    )

    elements = fetch_pois(lat, lon, _RADIUS_M)
    if elements is None:
        facts.append(
            ExtractedFact(
                field_name="location_error",
                value="donnees OpenStreetMap indisponibles (panne ou limite de requetes Overpass)",
                provenance=Provenance(source_type=SourceType.EXTERNAL_SOURCE, reference="Overpass API"),
            )
        )
        return {"document_facts": [f.model_dump(mode="json") for f in facts]}

    counts = aggregate_categories(elements)
    index = vibrancy_index(counts)
    osm_provenance = Provenance(
        source_type=SourceType.EXTERNAL_SOURCE,
        reference=f"OpenStreetMap/Overpass, rayon {_RADIUS_M}m",
    )

    for category, count in counts.items():
        facts.append(ExtractedFact(field_name=f"location_count:{category}", value=str(count), provenance=osm_provenance))
    facts.append(ExtractedFact(field_name="location_vibrancy_index", value=str(index), provenance=osm_provenance))

    result = analyze_location(payload.property_type, payload.location, counts, _RADIUS_M)

    if result.error:
        facts.append(
            ExtractedFact(
                field_name="location_error",
                value=f"analyse LLM de l'emplacement indisponible : {result.error}",
                provenance=Provenance(source_type=SourceType.EXTERNAL_SOURCE, reference="Groq"),
            )
        )
        return {"document_facts": [f.model_dump(mode="json") for f in facts]}

    facts.append(
        ExtractedFact(
            field_name="location_context",
            value=result.narrative,
            provenance=Provenance(source_type=SourceType.EXTERNAL_SOURCE, reference="Analyse LLM sur donnees OSM"),
        )
    )
    for opp in result.opportunities:
        facts.append(
            ExtractedFact(
                field_name=f"location_opportunity:{opp.type}",
                value=opp.description,
                provenance=Provenance(
                    source_type=SourceType.EXTERNAL_SOURCE,
                    reference="Analyse LLM sur donnees OSM",
                    confidence=opp.confidence,
                ),
            )
        )
    for risk in result.location_risks:
        facts.append(
            ExtractedFact(
                field_name="location_risk",
                value=risk.description,
                provenance=Provenance(
                    source_type=SourceType.EXTERNAL_SOURCE,
                    reference="Analyse LLM sur donnees OSM",
                    note=f"severity:{risk.severity}",
                ),
            )
        )

    return {"document_facts": [f.model_dump(mode="json") for f in facts]}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
