import os
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

from dealpilot_shared import ExtractedFact, PropertyRecord, Provenance, SourceType
from dealpilot_shared.logging_utils import CorrelationIdMiddleware, configure_logging

from .extraction import extract_structured_facts
from .text_extraction import extract_text

configure_logging("document-intel")

app = FastAPI(title="DealPilot AI — Document Intelligence")
app.add_middleware(CorrelationIdMiddleware)

UPLOAD_ROOT = Path(os.environ.get("UPLOAD_ROOT", "/data/uploads"))

NUMERIC_FIELDS = [
    "asking_price",
    "surface_m2",
    "units_total",
    "units_occupied",
    "monthly_rent",
    "annual_charges",
    "estimated_works",
]


class ExtractRequest(BaseModel):
    deal_id: str
    documents: list[str]
    property: PropertyRecord


@app.post("/extract")
def extract(payload: ExtractRequest) -> dict:
    property_record = payload.property
    document_facts: list[ExtractedFact] = []

    for filename in payload.documents:
        doc_path = UPLOAD_ROOT / payload.deal_id / "documents" / filename
        if not doc_path.exists():
            document_facts.append(
                ExtractedFact(
                    field_name="missing_file",
                    value=filename,
                    provenance=Provenance(source_type=SourceType.DOCUMENT, reference=filename),
                )
            )
            continue

        text = extract_text(doc_path)
        result = extract_structured_facts(text, filename)
        provenance = Provenance(source_type=SourceType.DOCUMENT, reference=filename)

        for field_name in NUMERIC_FIELDS:
            value = getattr(result, field_name)
            if value is not None:
                getattr(property_record, field_name).add(value, provenance)

        for fact in result.other_facts:
            document_facts.append(
                ExtractedFact(field_name=fact.field_name, value=fact.value, provenance=provenance)
            )

        if result.prompt_injection_detected:
            document_facts.append(
                ExtractedFact(
                    field_name="security_flag",
                    value=f"possible prompt injection attempt detected in {filename}",
                    provenance=provenance,
                )
            )

    return {
        "property": property_record.model_dump(mode="json"),
        "document_facts": [f.model_dump(mode="json") for f in document_facts],
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
