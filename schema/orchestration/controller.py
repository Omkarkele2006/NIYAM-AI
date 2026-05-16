"""
Governance-first orchestration controller for NIYAM-AI.

The controller is the bridge between proposal-only planning and the existing
proof-aware interceptor pipeline. It never executes planner output directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from schema.governance_service import run_governed_action
from schema.orchestration.proposal import (
    GovernedActionProposal,
    OrchestrationResult,
    PlannerOutput,
    ProposalExecutionRecord,
)
from schema.orchestration.secure_planner import SecurePlanner
from schema.orchestration.tool_registry import GovernedToolRegistry


@dataclass
class GovernanceOrchestrationController:
    """
    Secure controller for proposal-to-interceptor execution.

    Dependencies are injected so tests and demos can provide isolated contracts,
    control-flow policies, tool gates, planners, and tool registries. The
    planner receives no executable registry and no direct execution function.
    """

    planner: SecurePlanner
    tool_registry: GovernedToolRegistry
    contract: Any
    cfi: Any
    gate: Any

    def orchestrate(
        self,
        *,
        user_prompt: str,
        context: dict[str, Any] | None = None,
        stop_on_block: bool = True,
    ) -> OrchestrationResult:
        """
        Run a secure orchestration cycle.

        Flow:
            planner proposes actions
            -> proposals are shape-validated
            -> each proposal is bound to the sealed intent contract
            -> controller submits proposal to governance_service
            -> governance_service calls the existing interceptor
            -> interceptor owns validation, proof, verification, execution, audit
        """

        planner_output = self.planner.propose(
            user_prompt=user_prompt,
            contract=self.contract,
            context=context or {},
        )

        if not planner_output.proposals:
            return OrchestrationResult(
                task=user_prompt,
                session_id=getattr(self.contract, "session_id", None),
                intent_hash=self.contract.intent_hash(),
                planner_output=planner_output,
                records=[],
                status="NO_PROPOSALS",
            )

        records: list[ProposalExecutionRecord] = []

        for proposal in planner_output.proposals:
            record = self._submit_proposal(proposal)
            records.append(record)

            if stop_on_block and record.status in {"BLOCKED", "ERROR", "REJECTED"}:
                break

        return OrchestrationResult(
            task=user_prompt,
            session_id=getattr(self.contract, "session_id", None),
            intent_hash=self.contract.intent_hash(),
            planner_output=planner_output,
            records=records,
            status=_derive_orchestration_status(records, len(planner_output.proposals)),
        )

    def _submit_proposal(self, proposal: GovernedActionProposal) -> ProposalExecutionRecord:
        """Validate and submit one proposal into the existing interceptor path."""

        try:
            proposal.assert_safe_shape()
            bound_proposal = proposal.bind_contract(self.contract).with_status("SUBMITTED_TO_GOVERNANCE")

            result = run_governed_action(
                tool_name=bound_proposal.tool_name,
                payload=bound_proposal.payload,
                contract=self.contract,
                cfi=self.cfi,
                gate=self.gate,
                execute_func=self._execute_registered_tool,
            )

            proposal_status = "EXECUTED" if result.success else "BLOCKED" if result.status == "BLOCKED" else "ERROR"

            return ProposalExecutionRecord(
                proposal=bound_proposal.with_status(proposal_status),
                success=result.success,
                status=proposal_status,
                result=result.result,
                error=result.error,
            )

        except Exception as exc:
            safe_proposal = proposal.with_status("ERROR")
            return ProposalExecutionRecord(
                proposal=safe_proposal,
                success=False,
                status="ERROR",
                error=str(exc),
            )

    def _execute_registered_tool(self, tool_name: str, payload: dict[str, Any]) -> Any:
        """
        Execute a registered tool after interceptor approval.

        This function is passed into the existing interceptor. It is deliberately
        private to the controller and unavailable to planner implementations.
        """

        return self.tool_registry.execute(tool_name, payload)


def _derive_orchestration_status(
    records: list[ProposalExecutionRecord],
    proposal_count: int,
) -> str:
    """Summarize proposal execution records into an orchestration status."""

    if not records:
        return "NO_PROPOSALS"

    if any(record.status in {"BLOCKED", "REJECTED"} for record in records):
        return "BLOCKED"

    if any(record.status == "ERROR" for record in records):
        return "ERROR"

    if len(records) < proposal_count:
        return "PARTIAL"

    return "COMPLETED"
