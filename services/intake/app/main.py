import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile

from dealpilot_shared import FieldWithCandidates, FinancingAssumptions, PropertyRecord, Provenance, SourceType
from dealpilot_shared.logging_utils import CorrelationIdMiddleware, configure_logging

configure_logging("intake")

app = FastAPI(title="DealPilot AI — Intake")
app.add_middleware(CorrelationIdMiddleware)

UPLOAD_ROOT = Path(os.environ.get("UPLOAD_ROOT", "/data/uploads"))


def _field(value, provenance: Provenance) -> FieldWithCandidates:
    field: FieldWithCandidates = FieldWithCandidates()
    field.add(value, provenance)
    return field


def _save(upload: UploadFile, target_dir: Path) -> str:
    target_dir.mkdir(parents=True, exist_ok=True)
    dest = target_dir / upload.filename
    with dest.open("wb") as out:
        out.write(upload.file.read())
    return str(dest)


@app.post("/intake")
async def intake(
    deal_id: str = Form(...),
    property_type: str = Form(...),
    location: str = Form(...),
    address: str | None = Form(default=None),
    asking_price: float = Form(...),
    surface_m2: float = Form(...),
    units_total: int = Form(...),
    units_occupied: int = Form(...),
    monthly_rent: float = Form(...),
    annual_charges: float = Form(...),
    estimated_works: float = Form(...),
    listing_url: str | None = Form(default=None),
    known_missing_documents: str = Form(default=""),
    down_payment_pct: float = Form(default=20.0),
    interest_rate_pct: float = Form(default=4.0),
    loan_term_years: int = Form(default=20),
    vacancy_rate_pct: float = Form(default=5.0),
    exit_cap_rate_pct: float | None = Form(default=None),
    holding_period_years: int = Form(default=10),
    target_cap_rate_pct: float = Form(default=6.0),
    documents: list[UploadFile] = File(default=[]),
    photos: list[UploadFile] = File(default=[]),
) -> dict:
    deal_dir = UPLOAD_ROOT / deal_id
    stored_documents = [_save(f, deal_dir / "documents") for f in documents]
    stored_photos = [_save(f, deal_dir / "photos") for f in photos]

    provenance = Provenance(
        source_type=SourceType.EXTERNAL_SOURCE if listing_url else SourceType.USER_HYPOTHESIS,
        reference=listing_url or "user_intake_form",
    )

    record = PropertyRecord(
        id=str(uuid.uuid4()),
        property_type=property_type,
        location=location,
        address=address,
        asking_price=_field(asking_price, provenance),
        surface_m2=_field(surface_m2, provenance),
        units_total=_field(units_total, provenance),
        units_occupied=_field(units_occupied, provenance),
        monthly_rent=_field(monthly_rent, provenance),
        annual_charges=_field(annual_charges, provenance),
        estimated_works=_field(estimated_works, provenance),
        documents_received=[Path(p).name for p in stored_documents],
        documents_missing=[d.strip() for d in known_missing_documents.split(",") if d.strip()],
        photos_received=[Path(p).name for p in stored_photos],
    )

    financing_assumptions = FinancingAssumptions(
        down_payment_pct=down_payment_pct,
        interest_rate_pct=interest_rate_pct,
        loan_term_years=loan_term_years,
        vacancy_rate_pct=vacancy_rate_pct,
        exit_cap_rate_pct=exit_cap_rate_pct,
        holding_period_years=holding_period_years,
        target_cap_rate_pct=target_cap_rate_pct,
    )

    return {
        "property": record.model_dump(mode="json"),
        "financing_assumptions": financing_assumptions.model_dump(mode="json"),
        "document_paths": stored_documents,
        "photo_paths": stored_photos,
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
