"""
Typed proposal schemas for NIYAM-AI secure orchestration.

These models represent intent to execute, not permission to execute. A proposal
is never a tool call. It must still pass through the interceptor, proof
pipeline, verification, execution gate, and audit logger.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


ProposalStatus = Literal[
    "PROPOSED",
    "REJECTED",
    "SUBMITTED_TO_GOVERNANCE",
    "EXECUTED",
    "BLOCKED",
    "ERROR",
]


def utc_now_iso() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""

    return datetime.now(timezone.utc).isoformat()


def _contains_callable(value: Any) -> bool:
    """Detect callables recursively so proposals cannot smuggle execution."""

    if callable(value):
        return True

    if isinstance(value, dict):
        return any(_contains_callable(item) for item in value.values())

    if isinstance(value, (list, tuple, set)):
        return any(_contains_callable(item) for item in value)

    return False


def _model_to_dict(model: BaseModel) -> dict[str, Any]:
    """Return a pydantic-v1/v2 compatible dictionary."""

    if hasattr(model, "model_dump"):
        return model.model_dump()

    return model.dict()


class GovernedActionProposal(BaseModel):
    """
    A planner-generated request for a governed action.

    The proposal includes tool name and payload only as metadata for the
    governance runtime. It intentionally contains no execution callable, no
    registry reference, and no authority to bypass the interceptor.
    """

    proposal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str
    payload: dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""
    expected_effect: str = ""
    risk_notes: list[str] = Field(default_factory=list)
    planner_trace: list[str] = Field(default_factory=list)
    session_id: str | None = None
    intent_hash: str | None = None
    status: ProposalStatus = "PROPOSED"
    created_at: str = Field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def assert_safe_shape(self) -> None:
        """Reject proposal payloads that attempt to carry executable objects."""

        if not self.tool_name or not self.tool_name.strip():
            raise ValueError("Proposal tool_name is required.")

        if _contains_callable(self.payload):
            raise ValueError("Proposal payload cannot contain callable objects.")

        if _contains_callable(self.metadata):
            raise ValueError("Proposal metadata cannot contain callable objects.")

    def bind_contract(self, contract: Any) -> "GovernedActionProposal":
        """Attach contract identity without granting execution authority."""

        data = self.to_dict()
        data["session_id"] = getattr(contract, "session_id", None)
        data["intent_hash"] = contract.intent_hash()
        return GovernedActionProposal(**data)

    def with_status(self, status: ProposalStatus) -> "GovernedActionProposal":
        """Return a copy of this proposal with an updated lifecycle status."""

        data = self.to_dict()
        data["status"] = status
        return GovernedActionProposal(**data)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable proposal dictionary."""

        return _model_to_dict(self)


class PlannerOutput(BaseModel):
    """A planner response containing structured proposals only."""

    task: str
    proposals: list[GovernedActionProposal] = Field(default_factory=list)
    reasoning_summary: str = ""
    created_at: str = Field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable planner output dictionary."""

        return _model_to_dict(self)


class ProposalExecutionRecord(BaseModel):
    """Result of submitting one proposal to the governance runtime."""

    proposal: GovernedActionProposal
    success: bool
    status: ProposalStatus
    result: Any = None
    error: str | None = None
    completed_at: str = Field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable execution record."""

        return _model_to_dict(self)


class OrchestrationResult(BaseModel):
    """End-to-end result of one secure orchestration run."""

    task: str
    session_id: str | None
    intent_hash: str | None
    planner_output: PlannerOutput
    records: list[ProposalExecutionRecord] = Field(default_factory=list)
    status: Literal["COMPLETED", "PARTIAL", "BLOCKED", "NO_PROPOSALS", "ERROR"]
    created_at: str = Field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable orchestration result."""

        return _model_to_dict(self)
