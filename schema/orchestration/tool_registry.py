"""
Governed tool registry for NIYAM-AI.

The registry is owned by the runtime, not the planner. It provides explicit
allowlisted execution targets and deterministic metadata hashes for tool
identity, while actual authorization still happens in the existing tool gate.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Literal


ToolRisk = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


@dataclass(frozen=True)
class GovernedToolMetadata:
    """Describes a registered governed tool without exposing execution power."""

    name: str
    description: str
    risk_level: ToolRisk = "LOW"
    allowed_payload_keys: tuple[str, ...] = ()
    requires_proof: bool = True
    timeout_seconds: int = 10
    owner: str = "governance-runtime"

    @property
    def metadata_hash(self) -> str:
        """Return a deterministic SHA-256 hash of tool metadata."""

        normalized = json.dumps(
            {
                "name": self.name,
                "description": self.description,
                "risk_level": self.risk_level,
                "allowed_payload_keys": sorted(self.allowed_payload_keys),
                "requires_proof": self.requires_proof,
                "timeout_seconds": self.timeout_seconds,
                "owner": self.owner,
            },
            sort_keys=True,
        )
        return hashlib.sha256(normalized.encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """Return metadata in a frontend/log-friendly structure."""

        return {
            "name": self.name,
            "description": self.description,
            "risk_level": self.risk_level,
            "allowed_payload_keys": list(self.allowed_payload_keys),
            "requires_proof": self.requires_proof,
            "timeout_seconds": self.timeout_seconds,
            "owner": self.owner,
            "metadata_hash": self.metadata_hash,
        }


@dataclass
class GovernedToolRegistry:
    """
    Runtime-owned allowlist of executable tools.

    This object must never be passed into planner implementations. The
    orchestration controller uses it only after a proposal enters the governance
    runtime path.
    """

    _tools: dict[str, Callable[[dict[str, Any]], Any]] = field(default_factory=dict)
    _metadata: dict[str, GovernedToolMetadata] = field(default_factory=dict)

    def register(
        self,
        *,
        metadata: GovernedToolMetadata,
        handler: Callable[[dict[str, Any]], Any],
    ) -> None:
        """Register one governed tool handler with explicit metadata."""

        if not metadata.name:
            raise ValueError("Tool metadata name is required.")

        if not callable(handler):
            raise ValueError("Tool handler must be callable.")

        self._tools[metadata.name] = handler
        self._metadata[metadata.name] = metadata

    def has_tool(self, tool_name: str) -> bool:
        """Return whether a tool has been registered with the runtime."""

        return tool_name in self._tools

    def metadata_for(self, tool_name: str) -> GovernedToolMetadata:
        """Return metadata for a registered tool."""

        if tool_name not in self._metadata:
            raise KeyError(f"Tool '{tool_name}' is not registered.")

        return self._metadata[tool_name]

    def list_metadata(self) -> list[dict[str, Any]]:
        """Return all registered tool metadata."""

        return [metadata.to_dict() for metadata in self._metadata.values()]

    def execute(self, tool_name: str, payload: dict[str, Any]) -> Any:
        """
        Execute a registered tool handler.

        This method is only intended to be called by the interceptor after all
        governance checks and proof verification have passed.
        """

        if tool_name not in self._tools:
            raise PermissionError(f"Tool '{tool_name}' is not registered in governed runtime.")

        metadata = self._metadata[tool_name]

        if metadata.allowed_payload_keys:
            unexpected_keys = set(payload) - set(metadata.allowed_payload_keys)
            if unexpected_keys:
                raise ValueError(
                    f"Payload contains keys not declared in tool metadata: {sorted(unexpected_keys)}"
                )

        return self._tools[tool_name](payload)
