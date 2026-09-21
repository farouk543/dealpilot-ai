import asyncio
import os

import aiosqlite
import httpx
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph

from dealpilot_shared import (
    DueDiligencePackage,
    ExtractedFact,
    OfferStrategy,
    Provenance,
    PropertyRecord,
    RiskRegister,
    SourceType,
    UnderwritingResult,
    WorkflowStep,
)
from dealpilot_shared.logging_utils import get_correlation_id

from .config import settings
from .state import GraphState


def _corr_headers() -> dict[str, str]:
    return {"X-Correlation-ID": get_correlation_id()}

_STUB_SEQUENCE = [
    WorkflowStep.NORMALIZATION,
    WorkflowStep.FINAL_FILE,
]


def _make_stub_node(step: WorkflowStep):
    def node(state: GraphState) -> dict:
        deal = state.deal.model_copy(update={"current_step": step})
        return {"deal": deal}

    return node


async def _document_intelligence_node(state: GraphState) -> dict:
    deal = state.deal
    if deal.property is None or not deal.property.documents_received:
        return {"deal": deal.model_copy(update={"current_step": WorkflowStep.DOCUMENT_INTELLIGENCE})}

    payload = {
        "deal_id": deal.deal_id,
        "documents": deal.property.documents_received,
        "property": deal.property.model_dump(mode="json"),
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.document_intel_url}/extract", json=payload, headers=_corr_headers()
            )
            response.raise_for_status()
            result = response.json()
    except Exception as exc:
        error_fact = ExtractedFact(
            field_name="document_intel_error",
            value=f"service document-intel indisponible : {exc}",
            provenance=Provenance(source_type=SourceType.EXTERNAL_SOURCE, reference="document-intel"),
        )
        updated_deal = deal.model_copy(
            update={
                "current_step": WorkflowStep.DOCUMENT_INTELLIGENCE,
                "document_facts": deal.document_facts + [error_fact],
            }
        )
        return {"deal": updated_deal}

    updated_property = PropertyRecord.model_validate(result["property"])
    new_facts = [ExtractedFact.model_validate(f) for f in result.get("document_facts", [])]

    updated_deal = deal.model_copy(
        update={
            "property": updated_property,
            "current_step": WorkflowStep.DOCUMENT_INTELLIGENCE,
            "document_facts": deal.document_facts + new_facts,
        }
    )
    return {"deal": updated_deal}


async def _visual_analysis_node(state: GraphState) -> dict:
    deal = state.deal
    if deal.property is None or not deal.property.photos_received:
        return {"deal": deal.model_copy(update={"current_step": WorkflowStep.VISUAL_ANALYSIS})}

    payload = {"deal_id": deal.deal_id, "photos": deal.property.photos_received}
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{settings.vision_url}/analyze", json=payload, headers=_corr_headers())
            response.raise_for_status()
            result = response.json()
    except Exception as exc:
        error_fact = ExtractedFact(
            field_name="vision_error",
            value=f"service vision indisponible : {exc}",
            provenance=Provenance(source_type=SourceType.EXTERNAL_SOURCE, reference="vision"),
        )
        updated_deal = deal.model_copy(
            update={
                "current_step": WorkflowStep.VISUAL_ANALYSIS,
                "document_facts": deal.document_facts + [error_fact],
            }
        )
        return {"deal": updated_deal}

    new_facts = [ExtractedFact.model_validate(f) for f in result.get("document_facts", [])]
    updated_deal = deal.model_copy(
        update={
            "current_step": WorkflowStep.VISUAL_ANALYSIS,
            "document_facts": deal.document_facts + new_facts,
        }
    )
    return {"deal": updated_deal}


async def _fetch_market_comparables(client: httpx.AsyncClient, deal) -> list[dict]:
    payload = {
        "deal_id": deal.deal_id,
        "location": deal.property.location,
        "surface_m2": deal.property.surface_m2.resolved or deal.property.surface_m2.candidates[0].value,
    }
    try:
        response = await client.post(f"{settings.market_url}/comparables", json=payload, headers=_corr_headers())
        response.raise_for_status()
        return response.json().get("document_facts", [])
    except Exception as exc:
        # Found via failure-injection testing (case_09_adversarial_simulated_api_outage,
        # see eval/): without this, a market outage crashed the whole /deals request
        # with a 500, unlike every other downstream call which degrades gracefully.
        return [
            ExtractedFact(
                field_name="market_error",
                value=f"service market indisponible : {exc}",
                provenance=Provenance(source_type=SourceType.EXTERNAL_SOURCE, reference="market"),
            ).model_dump(mode="json")
        ]


async def _fetch_location_intel(client: httpx.AsyncClient, deal) -> list[dict]:
    payload = {
        "deal_id": deal.deal_id,
        "property_type": deal.property.property_type,
        "location": deal.property.location,
        "address": deal.property.address,
    }
    try:
        response = await client.post(f"{settings.location_intel_url}/analyze", json=payload, headers=_corr_headers())
        response.raise_for_status()
        return response.json().get("document_facts", [])
    except Exception as exc:
        return [
            ExtractedFact(
                field_name="location_error",
                value=f"service location-intel indisponible : {exc}",
                provenance=Provenance(source_type=SourceType.EXTERNAL_SOURCE, reference="location-intel"),
            ).model_dump(mode="json")
        ]


async def _market_analysis_node(state: GraphState) -> dict:
    deal = state.deal
    if deal.property is None:
        return {"deal": deal.model_copy(update={"current_step": WorkflowStep.MARKET_ANALYSIS})}

    async with httpx.AsyncClient(timeout=60.0) as client:
        market_facts_raw, location_facts_raw = await asyncio.gather(
            _fetch_market_comparables(client, deal), _fetch_location_intel(client, deal)
        )

    new_facts = [ExtractedFact.model_validate(f) for f in market_facts_raw + location_facts_raw]
    updated_deal = deal.model_copy(
        update={
            "current_step": WorkflowStep.MARKET_ANALYSIS,
            "document_facts": deal.document_facts + new_facts,
        }
    )
    return {"deal": updated_deal}


async def _financial_underwriting_node(state: GraphState) -> dict:
    deal = state.deal
    if deal.property is None:
        return {"deal": deal.model_copy(update={"current_step": WorkflowStep.FINANCIAL_UNDERWRITING})}

    payload = {
        "asking_price": deal.property.asking_price.resolved or deal.property.asking_price.candidates[0].value,
        "monthly_rent": deal.property.monthly_rent.resolved or deal.property.monthly_rent.candidates[0].value,
        "annual_charges": deal.property.annual_charges.resolved or deal.property.annual_charges.candidates[0].value,
        "estimated_works": deal.property.estimated_works.resolved or deal.property.estimated_works.candidates[0].value,
        "assumptions": deal.financing_assumptions.model_dump(mode="json"),
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.financial_engine_url}/underwrite", json=payload, headers=_corr_headers()
            )
            response.raise_for_status()
            result = response.json()
    except Exception as exc:
        error_fact = ExtractedFact(
            field_name="financial_engine_error",
            value=f"service financial-engine indisponible : {exc}",
            provenance=Provenance(source_type=SourceType.EXTERNAL_SOURCE, reference="financial-engine"),
        )
        updated_deal = deal.model_copy(
            update={
                "current_step": WorkflowStep.FINANCIAL_UNDERWRITING,
                "document_facts": deal.document_facts + [error_fact],
            }
        )
        return {"deal": updated_deal}

    updated_deal = deal.model_copy(
        update={
            "current_step": WorkflowStep.FINANCIAL_UNDERWRITING,
            "underwriting": UnderwritingResult.model_validate(result),
        }
    )
    return {"deal": updated_deal}


async def _risk_analysis_node(state: GraphState) -> dict:
    deal = state.deal
    if deal.property is None:
        return {"deal": deal.model_copy(update={"current_step": WorkflowStep.RISK_ANALYSIS})}

    payload = {
        "property": deal.property.model_dump(mode="json"),
        "document_facts": [f.model_dump(mode="json") for f in deal.document_facts],
        "underwriting": deal.underwriting.model_dump(mode="json") if deal.underwriting else None,
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{settings.risk_url}/assess", json=payload, headers=_corr_headers())
            response.raise_for_status()
            result = response.json()
    except Exception as exc:
        error_fact = ExtractedFact(
            field_name="risk_error",
            value=f"service risk indisponible : {exc}",
            provenance=Provenance(source_type=SourceType.EXTERNAL_SOURCE, reference="risk"),
        )
        updated_deal = deal.model_copy(
            update={
                "current_step": WorkflowStep.RISK_ANALYSIS,
                "document_facts": deal.document_facts + [error_fact],
            }
        )
        return {"deal": updated_deal}

    updated_deal = deal.model_copy(
        update={
            "current_step": WorkflowStep.RISK_ANALYSIS,
            "risk_register": RiskRegister.model_validate(result),
        }
    )
    return {"deal": updated_deal}


async def _offer_strategy_node(state: GraphState) -> dict:
    deal = state.deal
    if deal.property is None:
        return {"deal": deal.model_copy(update={"current_step": WorkflowStep.OFFER_STRATEGY})}

    payload = {
        "property": deal.property.model_dump(mode="json"),
        "underwriting": deal.underwriting.model_dump(mode="json") if deal.underwriting else None,
        "document_facts": [f.model_dump(mode="json") for f in deal.document_facts],
        "risk_register": deal.risk_register.model_dump(mode="json") if deal.risk_register else None,
        "assumptions": deal.financing_assumptions.model_dump(mode="json"),
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{settings.offer_url}/strategize", json=payload, headers=_corr_headers())
            response.raise_for_status()
            result = response.json()
    except Exception as exc:
        error_fact = ExtractedFact(
            field_name="offer_error",
            value=f"service offer indisponible : {exc}",
            provenance=Provenance(source_type=SourceType.EXTERNAL_SOURCE, reference="offer"),
        )
        updated_deal = deal.model_copy(
            update={
                "current_step": WorkflowStep.OFFER_STRATEGY,
                "document_facts": deal.document_facts + [error_fact],
            }
        )
        return {"deal": updated_deal}

    updated_deal = deal.model_copy(
        update={
            "current_step": WorkflowStep.OFFER_STRATEGY,
            "offer": OfferStrategy.model_validate(result),
        }
    )
    return {"deal": updated_deal}


async def _due_diligence_node(state: GraphState) -> dict:
    deal = state.deal

    payload = {"risk_register": deal.risk_register.model_dump(mode="json") if deal.risk_register else None}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{settings.due_diligence_url}/plan", json=payload, headers=_corr_headers())
            response.raise_for_status()
            result = response.json()
    except Exception as exc:
        error_fact = ExtractedFact(
            field_name="due_diligence_error",
            value=f"service due-diligence indisponible : {exc}",
            provenance=Provenance(source_type=SourceType.EXTERNAL_SOURCE, reference="due-diligence"),
        )
        updated_deal = deal.model_copy(
            update={
                "current_step": WorkflowStep.DUE_DILIGENCE,
                "document_facts": deal.document_facts + [error_fact],
            }
        )
        return {"deal": updated_deal}

    updated_deal = deal.model_copy(
        update={
            "current_step": WorkflowStep.DUE_DILIGENCE,
            "due_diligence": DueDiligencePackage.model_validate(result),
        }
    )
    return {"deal": updated_deal}


async def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node(WorkflowStep.NORMALIZATION.value, _make_stub_node(WorkflowStep.NORMALIZATION))
    graph.add_node(WorkflowStep.DOCUMENT_INTELLIGENCE.value, _document_intelligence_node)
    graph.add_node(WorkflowStep.VISUAL_ANALYSIS.value, _visual_analysis_node)
    graph.add_node(WorkflowStep.MARKET_ANALYSIS.value, _market_analysis_node)
    graph.add_node(WorkflowStep.FINANCIAL_UNDERWRITING.value, _financial_underwriting_node)
    graph.add_node(WorkflowStep.RISK_ANALYSIS.value, _risk_analysis_node)
    graph.add_node(WorkflowStep.OFFER_STRATEGY.value, _offer_strategy_node)
    graph.add_node(WorkflowStep.DUE_DILIGENCE.value, _due_diligence_node)
    for step in _STUB_SEQUENCE[1:]:
        graph.add_node(step.value, _make_stub_node(step))

    order = [
        WorkflowStep.NORMALIZATION,
        WorkflowStep.DOCUMENT_INTELLIGENCE,
        WorkflowStep.VISUAL_ANALYSIS,
        WorkflowStep.MARKET_ANALYSIS,
        WorkflowStep.FINANCIAL_UNDERWRITING,
        WorkflowStep.RISK_ANALYSIS,
        WorkflowStep.OFFER_STRATEGY,
        WorkflowStep.DUE_DILIGENCE,
        *_STUB_SEQUENCE[1:],
    ]
    previous = START
    for step in order:
        graph.add_edge(previous, step.value)
        previous = step.value
    graph.add_edge(previous, END)

    checkpointer = await _build_checkpointer()
    return graph.compile(checkpointer=checkpointer)


async def _build_checkpointer() -> AsyncSqliteSaver:
    # Persisted to a Docker volume: an orchestrator restart no longer loses
    # every in-progress dossier (previously an in-memory MemorySaver).
    db_path = os.environ.get("ORCHESTRATOR_DB_PATH", "/data/db/checkpoints.sqlite")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = await aiosqlite.connect(db_path)
    checkpointer = AsyncSqliteSaver(conn)
    await checkpointer.setup()
    return checkpointer
