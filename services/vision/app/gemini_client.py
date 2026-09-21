import base64
import json
import os

import httpx
from pydantic import BaseModel, Field

from dealpilot_shared.http_retry import with_retry

_API_KEY = os.environ.get("GEMINI_API_KEY", "")
_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{_MODEL}:generateContent"

_SYSTEM_INSTRUCTION = (
    "Tu es un assistant d'analyse visuelle immobiliere. Analyse la photo fournie et releve "
    "UNIQUEMENT des indices visibles (traces d'humidite, deterioration de surfaces, etat des "
    "finitions, equipements vieillissants, autres anomalies visibles). Tu ne dois JAMAIS "
    "affirmer une certification de securite structurelle : si un element est ambigu ou "
    "potentiellement structurel, mets needs_inspection=true. Donne un niveau de confiance "
    "realiste (0 a 1) pour chaque observation. Si la photo ne montre aucune anomalie visible, "
    "renvoie une liste vide."
)

_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "observations": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "indicator": {"type": "STRING"},
                    "description": {"type": "STRING"},
                    "confidence": {"type": "NUMBER"},
                    "needs_inspection": {"type": "BOOLEAN"},
                },
                "required": ["indicator", "description", "confidence", "needs_inspection"],
            },
        }
    },
    "required": ["observations"],
}


class VisionObservation(BaseModel):
    indicator: str
    description: str
    confidence: float
    needs_inspection: bool


class VisionAnalysisResult(BaseModel):
    observations: list[VisionObservation] = Field(default_factory=list)
    error: str | None = None


def analyze_image(image_bytes: bytes, mime_type: str, filename: str) -> VisionAnalysisResult:
    if not _API_KEY:
        return VisionAnalysisResult(error="GEMINI_API_KEY not configured")

    payload = {
        "system_instruction": {"parts": [{"text": _SYSTEM_INSTRUCTION}]},
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": f"Photo: {filename}"},
                    {"inline_data": {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()}},
                ],
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": _RESPONSE_SCHEMA,
            "temperature": 0,
        },
    }
    try:
        response = with_retry(lambda: httpx.post(f"{_ENDPOINT}?key={_API_KEY}", json=payload, timeout=60.0))
        response.raise_for_status()
        data = response.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
        return VisionAnalysisResult(observations=[VisionObservation(**o) for o in parsed.get("observations", [])])
    except Exception as exc:
        return VisionAnalysisResult(error=str(exc))
