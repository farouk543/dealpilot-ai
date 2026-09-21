import os
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

from dealpilot_shared import ExtractedFact, Provenance, SourceType
from dealpilot_shared.logging_utils import CorrelationIdMiddleware, configure_logging

from .gemini_client import analyze_image

configure_logging("vision")

app = FastAPI(title="DealPilot AI — Vision")
app.add_middleware(CorrelationIdMiddleware)

UPLOAD_ROOT = Path(os.environ.get("UPLOAD_ROOT", "/data/uploads"))

_MIME_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}

_DISCLAIMER = (
    "Analyse visuelle indicative uniquement ; ne constitue pas une expertise "
    "ou certification structurelle."
)


class AnalyzeRequest(BaseModel):
    deal_id: str
    photos: list[str]


@app.post("/analyze")
def analyze(payload: AnalyzeRequest) -> dict:
    facts: list[ExtractedFact] = []

    for filename in payload.photos:
        photo_path = UPLOAD_ROOT / payload.deal_id / "photos" / filename
        mime_type = _MIME_TYPES.get(photo_path.suffix.lower())

        if not photo_path.exists() or mime_type is None:
            facts.append(
                ExtractedFact(
                    field_name="vision_error",
                    value=f"unreadable or unsupported photo: {filename}",
                    provenance=Provenance(source_type=SourceType.VISION_ANALYSIS, reference=filename),
                )
            )
            continue

        result = analyze_image(photo_path.read_bytes(), mime_type, filename)
        if result.error:
            facts.append(
                ExtractedFact(
                    field_name="vision_error",
                    value=f"{filename}: {result.error}",
                    provenance=Provenance(source_type=SourceType.VISION_ANALYSIS, reference=filename),
                )
            )
            continue

        for obs in result.observations:
            facts.append(
                ExtractedFact(
                    field_name=f"visual:{obs.indicator}",
                    value=obs.description,
                    provenance=Provenance(
                        source_type=SourceType.VISION_ANALYSIS,
                        reference=filename,
                        confidence=obs.confidence,
                        note="needs_professional_inspection" if obs.needs_inspection else None,
                    ),
                )
            )

    if payload.photos:
        facts.append(
            ExtractedFact(
                field_name="vision_disclaimer",
                value=_DISCLAIMER,
                provenance=Provenance(source_type=SourceType.VISION_ANALYSIS, reference="system"),
            )
        )

    return {"document_facts": [f.model_dump(mode="json") for f in facts]}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
