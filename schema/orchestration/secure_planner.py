"""
Secure planner interfaces for NIYAM-AI.

Planners are intentionally powerless: they can reason, decompose tasks, and
emit governed action proposals, but they cannot access tool callables or execute
anything directly.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

from schema.orchestration.proposal import GovernedActionProposal, PlannerOutput


class SecurePlanner(ABC):
    """
    Abstract proposal-only planner.

    Implementations must never execute tools, import tool registries, call
    subprocesses, mutate contracts, or bypass the governance runtime.
    """

    @abstractmethod
    def propose(
        self,
        *,
        user_prompt: str,
        contract: Any,
        context: dict[str, Any] | None = None,
    ) -> PlannerOutput:
        """Return structured action proposals for governance review."""


class RuleBasedSecurePlanner(SecurePlanner):
    """
    Conservative starter planner for governed demos.

    This is not a chatbot agent and not a tool executor. It performs simple task
    decomposition and emits structured proposals that must still pass through
    the interceptor and proof-aware governance runtime.
    """

    def propose(
        self,
        *,
        user_prompt: str,
        contract: Any,
        context: dict[str, Any] | None = None,
    ) -> PlannerOutput:
        context = context or {}
        prompt = user_prompt.lower()

        proposals: list[GovernedActionProposal] = []

        if any(token in prompt for token in ["email", "mail", "send details"]):
            proposals.append(
                GovernedActionProposal(
                    tool_name="send_email",
                    payload={
                        "to": context.get("email_recipient", "unknown"),
                        "data": user_prompt,
                    },
                    rationale="Prompt requested email-style exfiltration or communication.",
                    expected_effect="Governance runtime should evaluate and likely block if forbidden.",
                    risk_notes=["potential_forbidden_tool", "possible_data_exfiltration"],
                    planner_trace=["Detected email-related intent in user prompt."],
                )
            )

        if any(token in prompt for token in ["transaction", "payment", "pay", "transfer"]):
            proposals.append(
                GovernedActionProposal(
                    tool_name="proceed_transaction",
                    payload={
                        "amount": _extract_amount(user_prompt) or context.get("amount", 100),
                        "recipient": context.get("recipient", "user1"),
                    },
                    rationale="Prompt requested a transaction-like action.",
                    expected_effect="Governance runtime should validate, prove, verify, then execute.",
                    risk_notes=["financial_action"],
                    planner_trace=["Detected transaction-related intent in user prompt."],
                )
            )

        if not proposals:
            proposals.append(
                GovernedActionProposal(
                    tool_name=str(context.get("default_tool", "proceed_transaction")),
                    payload=dict(context.get("default_payload", {"amount": 100, "recipient": "user1"})),
                    rationale="No specialized planner pattern matched; emitted conservative default proposal.",
                    expected_effect="Governance runtime decides whether this proposal is allowed.",
                    risk_notes=["default_proposal"],
                    planner_trace=["No direct execution attempted by planner."],
                )
            )

        return PlannerOutput(
            task=user_prompt,
            proposals=proposals,
            reasoning_summary=(
                "Planner emitted structured action proposals only. "
                "Execution authority remains with the governance runtime."
            ),
        )


def _extract_amount(text: str) -> int | None:
    """Extract a simple integer amount from prompt text when present."""

    match = re.search(r"(?:rs\.?|inr|\$)?\s*(\d{1,9})", text.lower())
    if not match:
        return None

    return int(match.group(1))
