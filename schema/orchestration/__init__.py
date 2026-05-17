"""
Secure orchestration layer for NIYAM-AI.

The orchestration package is deliberately proposal-first and interceptor-first:
planners can only emit structured action proposals, while execution remains
owned by the governance runtime.

NOTE — GovernanceOrchestrationController is intentionally NOT imported at
package level.  controller.py imports governance_service.run_governed_action,
and governance_service imports interceptor, which imports execution_runtime
from this package.  Eagerly importing the controller here would create a
circular dependency:

    governance_service → interceptor → orchestration.__init__
        → controller → governance_service  (💥 partially initialized)

Callers that need the controller should import it directly:

    from schema.orchestration.controller import GovernanceOrchestrationController
"""

from schema.orchestration.execution_runtime import (
    ExecutionState,
    GovernedExecutionContext,
    GovernedExecutionResult,
    GovernedExecutionRuntime,
    RuntimeGovernanceEvent,
    derive_execution_id,
)
from schema.orchestration.proposal import GovernedActionProposal, OrchestrationResult
from schema.orchestration.secure_planner import RuleBasedSecurePlanner, SecurePlanner
from schema.orchestration.tool_registry import GovernedToolMetadata, GovernedToolRegistry

__all__ = [
    "ExecutionState",
    "GovernedActionProposal",
    "GovernedExecutionContext",
    "GovernedExecutionResult",
    "GovernedExecutionRuntime",
    "GovernedToolMetadata",
    "GovernedToolRegistry",
    "OrchestrationResult",
    "RuleBasedSecurePlanner",
    "RuntimeGovernanceEvent",
    "SecurePlanner",
    "derive_execution_id",
]

