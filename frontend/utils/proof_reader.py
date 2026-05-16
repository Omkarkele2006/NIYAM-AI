"""
Frontend-safe proof artifact helpers for NIYAM-AI.

The functions in this module expose existing zkML proof and witness artifacts
in a Streamlit-friendly shape. They do not generate proofs or alter verifier
behavior.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any


FRONTEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = FRONTEND_ROOT.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from schema.governance_service import (  # noqa: E402
    PROOF_PATH,
    VK_PATH,
    WITNESS_PATH,
    load_latest_proof,
    load_witness_data,
    verify_proof_status,
)


def _sha256_file(path: Path) -> str | None:
    """Return the SHA-256 hash of a file, or None when absent."""

    if not path.exists():
        return None

    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def get_latest_proof_metadata() -> dict[str, Any]:
    """Return metadata and parsed JSON for the latest proof artifact."""

    proof = load_latest_proof()
    proof["sha256"] = _sha256_file(Path(proof["path"]))
    return proof


def get_witness_artifact() -> dict[str, Any]:
    """Return metadata and parsed JSON for the latest witness artifact."""

    witness = load_witness_data()
    witness["sha256"] = _sha256_file(Path(witness["path"]))
    return witness


def get_verification_status() -> dict[str, Any]:
    """Return current proof verification status using the service layer."""

    return verify_proof_status()


def get_verification_key_metadata() -> dict[str, Any]:
    """Return verification-key metadata and SHA-256 visibility."""

    path = VK_PATH
    return {
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "sha256": _sha256_file(path),
    }


def get_proof_artifact_overview() -> dict[str, Any]:
    """Return a compact proof, witness, key, and verification overview."""

    proof = get_latest_proof_metadata()
    witness = get_witness_artifact()
    verification = get_verification_status()
    verification_key = get_verification_key_metadata()

    return {
        "proof": proof,
        "witness": witness,
        "verification": verification,
        "verification_key": verification_key,
        "paths": {
            "proof": str(PROOF_PATH),
            "witness": str(WITNESS_PATH),
            "verification_key": str(VK_PATH),
        },
    }
