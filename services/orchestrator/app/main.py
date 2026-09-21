import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from dealpilot_shared import (
    BuildingDesignBrief,
    DealState,
    Facade360Request,
    FinancingAssumptions,
    InteriorRenderRequest,
    LandConstraints,
    PropertyRecord,
    WorkflowStep,
)
from dealpilot_shared.logging_utils import CorrelationIdMiddleware, configure_logging, get_correlation_id, set_correlation_id

from .config import settings
from .graph import build_graph
from .state import GraphState

configure_logging("orchestrator")

_graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _graph
    # The checkpointer (AsyncSqliteSaver) needs an event loop to open its
    # connection, so the graph is built here rather than at import time.
    _graph = await build_graph()
    yield


app = FastAPI(title="DealPilot AI — Orchestrator", lifespan=lifespan)
app.add_middleware(CorrelationIdMiddleware)


@app.post("/deals")
async def create_deal(
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
    deal_id = str(uuid.uuid4())
    # The deal_id becomes the correlation ID for everything this deal touches
    # from here on — every log line and every downstream service call for
    # this dossier, across all 13 microservices, carries it.
    set_correlation_id(deal_id)

    data = {
        "deal_id": deal_id,
        "property_type": property_type,
        "location": location,
        "asking_price": asking_price,
        "surface_m2": surface_m2,
        "units_total": units_total,
        "units_occupied": units_occupied,
        "monthly_rent": monthly_rent,
        "annual_charges": annual_charges,
        "estimated_works": estimated_works,
        "known_missing_documents": known_missing_documents,
        "down_payment_pct": down_payment_pct,
        "interest_rate_pct": interest_rate_pct,
        "loan_term_years": loan_term_years,
        "vacancy_rate_pct": vacancy_rate_pct,
        "holding_period_years": holding_period_years,
        "target_cap_rate_pct": target_cap_rate_pct,
    }
    if listing_url:
        data["listing_url"] = listing_url
    if address:
        data["address"] = address
    if exit_cap_rate_pct is not None:
        data["exit_cap_rate_pct"] = exit_cap_rate_pct

    files = [("documents", (f.filename, await f.read(), f.content_type)) for f in documents]
    files += [("photos", (f.filename, await f.read(), f.content_type)) for f in photos]

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.intake_url}/intake", data=data, files=files, headers={"X-Correlation-ID": deal_id}
        )
        response.raise_for_status()
        intake_result = response.json()

    property_record = PropertyRecord.model_validate(intake_result["property"])
    financing_assumptions = FinancingAssumptions.model_validate(intake_result["financing_assumptions"])
    deal = DealState(
        deal_id=deal_id,
        property=property_record,
        financing_assumptions=financing_assumptions,
        current_step=WorkflowStep.INTAKE,
    )

    config = {"configurable": {"thread_id": deal_id}}
    result = await _graph.ainvoke(GraphState(deal=deal), config=config)
    return result["deal"].model_dump(mode="json")


async def _get_deal_or_404(deal_id: str) -> DealState:
    set_correlation_id(deal_id)
    config = {"configurable": {"thread_id": deal_id}}
    state = await _graph.aget_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="deal not found")
    return state.values["deal"]


@app.get("/deals/compare")
async def compare_deals(ids: str) -> dict:
    deal_ids = [d.strip() for d in ids.split(",") if d.strip()]
    results = []
    for deal_id in deal_ids:
        try:
            deal = await _get_deal_or_404(deal_id)
        except HTTPException:
            results.append({"deal_id": deal_id, "error": "dossier introuvable"})
            continue

        base = None
        if deal.underwriting:
            scenarios = deal.underwriting.model_dump(mode="json")["scenarios"]
            base = next((s for s in scenarios if s["name"] == "base"), None)

        results.append(
            {
                "deal_id": deal_id,
                "property_type": deal.property.property_type if deal.property else None,
                "location": deal.property.location if deal.property else None,
                "asking_price": (
                    deal.property.asking_price.resolved or deal.property.asking_price.candidates[0].value
                )
                if deal.property and deal.property.asking_price.candidates
                else None,
                "cap_rate_pct": base["cap_rate_pct"] if base else None,
                "cash_on_cash_pct": base["cash_on_cash_pct"] if base else None,
                "dscr": base["dscr"] if base else None,
                "offer_target_price": deal.offer.target_price if deal.offer else None,
                "risk_count": len(deal.risk_register.risks) if deal.risk_register else 0,
                "decision_ready": deal.due_diligence.decision_ready if deal.due_diligence else None,
            }
        )
    return {"deals": results}


@app.get("/deals/{deal_id}")
async def get_deal(deal_id: str) -> dict:
    deal = await _get_deal_or_404(deal_id)
    return deal.model_dump(mode="json")


class CounterOfferRequest(BaseModel):
    counter_price: float


@app.post("/deals/{deal_id}/counter-offer")
async def counter_offer(deal_id: str, payload: CounterOfferRequest) -> dict:
    deal = await _get_deal_or_404(deal_id)
    if deal.property is None or deal.underwriting is None:
        raise HTTPException(status_code=400, detail="dossier pas encore souscrit financierement")

    prop = deal.property
    underwrite_payload = {
        "asking_price": payload.counter_price,
        "monthly_rent": prop.monthly_rent.resolved or prop.monthly_rent.candidates[0].value,
        "annual_charges": prop.annual_charges.resolved or prop.annual_charges.candidates[0].value,
        "estimated_works": prop.estimated_works.resolved or prop.estimated_works.candidates[0].value,
        "assumptions": deal.financing_assumptions.model_dump(mode="json"),
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.financial_engine_url}/underwrite",
            json=underwrite_payload,
            headers={"X-Correlation-ID": deal_id},
        )
        response.raise_for_status()
        new_underwriting = response.json()

    original_base = next(s for s in deal.underwriting.model_dump(mode="json")["scenarios"] if s["name"] == "base")
    new_base = next(s for s in new_underwriting["scenarios"] if s["name"] == "base")

    offer = deal.offer
    if offer is None or offer.max_price is None:
        recommendation = "Pas de seuil d'offre calculé pour ce dossier — comparer les chiffres ci-dessous manuellement."
    elif payload.counter_price <= (offer.target_price or offer.max_price):
        recommendation = "Au niveau ou sous le prix cible initial : accepter."
    elif payload.counter_price <= offer.max_price:
        recommendation = "Au-dessus du prix cible mais sous le prix maximum acceptable calculé : négociable, acceptable."
    else:
        recommendation = (
            f"Dépasse le prix maximum acceptable calculé ({offer.max_price:,.0f} €) : refuser ou contre-attaquer."
        )

    return {
        "counter_price": payload.counter_price,
        "original_price": prop.asking_price.resolved or prop.asking_price.candidates[0].value,
        "original_base_scenario": original_base,
        "updated_base_scenario": new_base,
        "offer_target_price": offer.target_price if offer else None,
        "offer_max_price": offer.max_price if offer else None,
        "recommendation": recommendation,
    }


@app.get("/deals/{deal_id}/summary")
async def deal_summary(deal_id: str) -> dict:
    deal = await _get_deal_or_404(deal_id)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.summary_url}/summarize",
            json={"deal": deal.model_dump(mode="json")},
            headers={"X-Correlation-ID": deal_id},
        )
        response.raise_for_status()
        return response.json()


@app.get("/deals/{deal_id}/export.pdf")
async def export_deal_pdf(deal_id: str) -> Response:
    deal = await _get_deal_or_404(deal_id)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.report_url}/export/pdf",
            json={"deal": deal.model_dump(mode="json")},
            headers={"X-Correlation-ID": deal_id},
        )
        response.raise_for_status()
        return Response(
            content=response.content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=dealpilot_{deal_id}.pdf"},
        )


@app.get("/deals/{deal_id}/export.xlsx")
async def export_deal_xlsx(deal_id: str) -> Response:
    deal = await _get_deal_or_404(deal_id)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.report_url}/export/xlsx",
            json={"deal": deal.model_dump(mode="json")},
            headers={"X-Correlation-ID": deal_id},
        )
        response.raise_for_status()
        return Response(
            content=response.content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=dealpilot_{deal_id}.xlsx"},
        )


class DevelopmentProFormaRequest(BaseModel):
    land_cost: float
    construction_cost_per_m2: float
    surface_to_build_m2: float
    soft_costs_pct: float = 12.0
    estimated_exit_value: float


class ChatMessagePayload(BaseModel):
    role: str
    content: str


class DesignChatRequest(BaseModel):
    history: list[ChatMessagePayload]
    feasibility_context: str | None = None


@app.post("/land/feasibility")
async def land_feasibility(constraints: LandConstraints) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.land_feasibility_url}/feasibility",
            json=constraints.model_dump(),
            headers={"X-Correlation-ID": get_correlation_id()},
        )
        response.raise_for_status()
        return response.json()


@app.post("/land/proforma")
async def land_proforma(payload: DevelopmentProFormaRequest) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.financial_engine_url}/underwrite-development",
            json=payload.model_dump(),
            headers={"X-Correlation-ID": get_correlation_id()},
        )
        response.raise_for_status()
        return response.json()


@app.post("/land/chat")
async def land_chat(payload: DesignChatRequest) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.design_agent_url}/chat",
            json=payload.model_dump(),
            headers={"X-Correlation-ID": get_correlation_id()},
        )
        response.raise_for_status()
        return response.json()


@app.post("/land/interior")
async def land_interior(payload: InteriorRenderRequest) -> dict:
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.interior_render_url}/generate",
            json=payload.model_dump(),
            headers={"X-Correlation-ID": get_correlation_id()},
        )
        response.raise_for_status()
        return response.json()


@app.post("/land/facade-360")
async def land_facade_360(payload: Facade360Request) -> dict:
    # 8 sequential SDXL generations behind the GPU lock — generous timeout,
    # this can take several minutes end to end.
    async with httpx.AsyncClient(timeout=600.0) as client:
        response = await client.post(
            f"{settings.interior_render_url}/generate-360",
            json=payload.model_dump(),
            headers={"X-Correlation-ID": get_correlation_id()},
        )
        response.raise_for_status()
        return response.json()


@app.post("/land/massing")
async def land_massing(payload: BuildingDesignBrief) -> dict:
    async with httpx.AsyncClient(timeout=200.0) as client:
        response = await client.post(
            f"{settings.exterior_render_url}/render",
            json=payload.model_dump(),
            headers={"X-Correlation-ID": get_correlation_id()},
        )
        response.raise_for_status()
        return response.json()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
