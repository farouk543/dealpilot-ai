from fastapi import FastAPI
from pydantic import BaseModel

from dealpilot_shared.logging_utils import CorrelationIdMiddleware, configure_logging

from .conversation import ChatMessage, run_turn

configure_logging("design-agent")

app = FastAPI(title="DealPilot AI — Design Agent")
app.add_middleware(CorrelationIdMiddleware)


class ChatRequest(BaseModel):
    history: list[ChatMessage]
    feasibility_context: str | None = None


@app.post("/chat")
def chat(payload: ChatRequest) -> dict:
    result = run_turn(payload.history, payload.feasibility_context)
    return result.model_dump(mode="json")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
