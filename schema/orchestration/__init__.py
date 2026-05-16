"""
Secure orchestration layer for NIYAM-AI.

The orchestration package is deliberately proposal-first and interceptor-first:
planners can only emit structured action proposals, while execution remains
owned by the governance runtime.
"""

from schema.orchestration.controller import GovernanceOrchestrationController
from schema.orchestration.proposal import GovernedActionProposal, OrchestrationResult
from schema.orchestration.secure_planner import RuleBasedSecurePlanner, SecurePlanner
from schema.orchestration.tool_registry import GovernedToolMetadata, GovernedToolRegistry

__all__ = [
    "GovernanceOrchestrationController",
    "GovernedActionProposal",
    "GovernedToolMetadata",
    "GovernedToolRegistry",
    "OrchestrationResult",
    "RuleBasedSecurePlanner",
    "SecurePlanner",
]
