from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel

from dealpilot_shared.logging_utils import CorrelationIdMiddleware, configure_logging

from .pdf_report import build_pdf
from .xlsx_report import build_xlsx

configure_logging("report")

app = FastAPI(title="DealPilot AI — Report")
app.add_middleware(CorrelationIdMiddleware)


class ExportRequest(BaseModel):
    deal: dict


@app.post("/export/pdf")
def export_pdf(payload: ExportRequest) -> Response:
    pdf_bytes = build_pdf(payload.deal)
    filename = f"dealpilot_{payload.deal.get('deal_id', 'dossier')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.post("/export/xlsx")
def export_xlsx(payload: ExportRequest) -> Response:
    xlsx_bytes = build_xlsx(payload.deal)
    filename = f"dealpilot_{payload.deal.get('deal_id', 'dossier')}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
