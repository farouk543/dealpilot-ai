from fastapi import FastAPI
from pydantic import BaseModel

from dealpilot_shared.logging_utils import CorrelationIdMiddleware, configure_logging

from .narrative import summarize_deal

configure_logging("summary")

app = FastAPI(title="DealPilot AI — Summary")
app.add_middleware(CorrelationIdMiddleware)


class SummarizeRequest(BaseModel):
    deal: dict


@app.post("/summarize")
def summarize(payload: SummarizeRequest) -> dict:
    result = summarize_deal(payload.deal)
    return result.model_dump(mode="json")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
