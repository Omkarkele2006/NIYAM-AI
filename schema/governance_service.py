"""
Governance service layer for NIYAM-AI.

This module is the intended boundary between the Streamlit frontend and the
backend security pipeline. It keeps UI code away from low-level interceptor,
EZKL, proof, witness, and audit-log details while preserving the existing
backend behavior.
"""

from __future__ import annotations

import json
import os
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from schema.interceptor import InterceptionBlocked, intercept_execution
from schema.verifier import verify_proof


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_LOG_PATH = REPO_ROOT / "audit_log.jsonl"
PROOF_PATH = REPO_ROOT / "proof.json"
WITNESS_PATH = REPO_ROOT / "witness.json"
INPUT_PATH = REPO_ROOT / "input.json"
VK_PATH = REPO_ROOT / "vk.key"
CIRCUIT_PATH = REPO_ROOT / "circuit.ezkl"

_CWD_LOCK = threading.RLock()


@dataclass(frozen=True)
class GovernanceRunResult:
    """
    Structured result returned after a governed action attempt.

    The service catches interceptor exceptions so frontend callers can render
    clean states without needing to know backend exception types.
    """

    success: bool
    status: str
    tool_name: str
    result: Any = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the run result."""

        return {
            "success": self.success,
            "status": self.status,
            "tool_name": self.tool_name,
            "result": self.result,
            "error": self.error,
        }


@contextmanager
def _repo_cwd() -> Iterable[None]:
    """
    Run existing backend code from the repository root.

    The current interceptor and EZKL modules use repo-root relative artifact
    paths. This context manager preserves that behavior while allowing
    Streamlit pages to be launched from another working directory.
    """

    with _CWD_LOCK:
        previous_cwd = Path.cwd()
        os.chdir(REPO_ROOT)
        try:
            yield
        finally:
            os.chdir(previous_cwd)


def _utc_timestamp(path: Path) -> str | None:
    """Return a file modification timestamp in UTC ISO-8601 format."""

    if not path.exists():
        return None

    modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return modified_at.isoformat()


def _load_json(path: Path) -> dict[str, Any] | list[Any] | None:
    """Safely load a JSON file and return None when the artifact is absent."""

    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _artifact_summary(path: Path) -> dict[str, Any]:
    """Return existence and metadata for a repository artifact."""

    return {
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "modified_at": _utc_timestamp(path),
    }


def run_governed_action(
    *,
    tool_name: str,
    payload: dict[str, Any],
    contract: Any,
    cfi: Any,
    gate: Any,
    execute_func: Callable[[str, dict[str, Any]], Any],
) -> GovernanceRunResult:
    """
    Run one action through the existing NIYAM-AI governance pipeline.

    This is a thin service wrapper over ``intercept_execution``. It does not
    change policy checks, feature extraction, proof generation, proof
    verification, execution, or audit logging.
    """

    try:
        with _repo_cwd():
            result = intercept_execution(
                tool_name=tool_name,
                payload=payload,
                contract=contract,
                cfi=cfi,
                gate=gate,
                execute_func=execute_func,
            )

        return GovernanceRunResult(
            success=True,
            status="EXECUTED",
            tool_name=tool_name,
            result=result,
        )

    except InterceptionBlocked as exc:
        return GovernanceRunResult(
            success=False,
            status="BLOCKED",
            tool_name=tool_name,
            error=str(exc),
        )
    except Exception as exc:
        return GovernanceRunResult(
            success=False,
            status="ERROR",
            tool_name=tool_name,
            error=str(exc),
        )


def load_audit_logs(
    *,
    limit: int | None = None,
    status: str | None = None,
    log_path: Path = AUDIT_LOG_PATH,
) -> list[dict[str, Any]]:
    """
    Load audit log records from the append-only JSONL log.

    Invalid or empty lines are skipped so the frontend can keep rendering even
    if a partial write appears during a live run.
    """

    path = Path(log_path)
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            if status is None or record.get("status") == status:
                records.append(record)

    if limit is not None and limit >= 0:
        return records[-limit:]

    return records


def load_latest_proof(proof_path: Path = PROOF_PATH) -> dict[str, Any]:
    """
    Load the latest proof artifact with metadata.

    The current pipeline writes a single ``proof.json`` artifact. This function
    exposes it in a frontend-safe shape without changing that convention.
    """

    path = Path(proof_path)
    return {
        **_artifact_summary(path),
        "data": _load_json(path),
    }


def load_witness_data(witness_path: Path = WITNESS_PATH) -> dict[str, Any]:
    """
    Load the latest witness artifact with metadata.

    The witness is generated by the existing EZKL pipeline and returned as-is
    for inspection pages such as a proof explorer.
    """

    path = Path(witness_path)
    return {
        **_artifact_summary(path),
        "data": _load_json(path),
    }


def verify_proof_status(proof_path: Path = PROOF_PATH) -> dict[str, Any]:
    """
    Verify the latest proof using the existing verifier.

    Returns a structured status object for UI rendering. Verification itself is
    delegated to ``schema.verifier.verify_proof`` so backend security behavior
    remains unchanged.
    """

    path = Path(proof_path)

    if not path.exists():
        return {
            "verified": False,
            "status": "MISSING_PROOF",
            "proof_path": str(path),
            "error": "Proof artifact not found.",
        }

    try:
        with _repo_cwd():
            verified = verify_proof(str(path))

        return {
            "verified": verified,
            "status": "VERIFIED" if verified else "FAILED",
            "proof_path": str(path),
            "error": None,
        }

    except Exception as exc:
        return {
            "verified": False,
            "status": "ERROR",
            "proof_path": str(path),
            "error": str(exc),
        }


def get_system_metrics() -> dict[str, Any]:
    """
    Compute high-level governance metrics for dashboard pages.

    Metrics are derived from audit logs and root-level artifacts only; no proof
    generation, model execution, or verification is triggered here.
    """

    logs = load_audit_logs()
    executed = [row for row in logs if row.get("status") == "EXECUTED"]
    blocked = [row for row in logs if row.get("status") == "BLOCKED"]
    errors = [row for row in logs if row.get("status") == "ERROR"]
    verified = [row for row in logs if row.get("verification") is True]

    latest_record = logs[-1] if logs else None
    unique_sessions = {
        row.get("session_id")
        for row in logs
        if row.get("session_id")
    }

    return {
        "total_actions": len(logs),
        "executed_actions": len(executed),
        "blocked_actions": len(blocked),
        "error_actions": len(errors),
        "verified_proofs": len(verified),
        "unique_sessions": len(unique_sessions),
        "latest_record": latest_record,
        "latest_timestamp": latest_record.get("timestamp") if latest_record else None,
        "artifacts": {
            "proof": _artifact_summary(PROOF_PATH),
            "witness": _artifact_summary(WITNESS_PATH),
            "input": _artifact_summary(INPUT_PATH),
            "verification_key": _artifact_summary(VK_PATH),
            "circuit": _artifact_summary(CIRCUIT_PATH),
        },
    }

