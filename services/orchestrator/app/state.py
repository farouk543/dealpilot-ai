import operator
from typing import Annotated

from pydantic import BaseModel, Field

from dealpilot_shared import ApprovalRequest, DealState


class GraphState(BaseModel):
    """LangGraph state for one deal run.

    Kept separate from dealpilot_shared.DealState so framework-specific
    concerns (reducer annotations) don't leak into the cross-service contract.
    """

    deal: DealState
    approval_log: Annotated[list[ApprovalRequest], operator.add] = Field(default_factory=list)
