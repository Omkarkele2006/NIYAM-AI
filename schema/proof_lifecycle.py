import os
import subprocess
import hashlib
import json
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]

TRUSTED_VK_HASH = "f519d8bddcf2801c194fb65e7d1ef628497462443e0891081e52c47bd99956e1"

REQUIRED_FILES = [
    "model.onnx",
    "circuit.ezkl",
    "settings.json",
    "vk.key",
    "pk.key",
    "kzg.srs"
]

class ProofState(Enum):
    """FSM Lifecycle states for a single zkML proof verification run."""
    PROOF_PENDING = "PROOF_PENDING"
    PROOF_GENERATING = "PROOF_GENERATING"
    PROOF_GENERATED = "PROOF_GENERATED"
    PROOF_VERIFYING = "PROOF_VERIFYING"
    PROOF_VERIFIED = "PROOF_VERIFIED"
    PROOF_FAILED = "PROOF_FAILED"
    PROOF_MISSING = "PROOF_MISSING"
    PROOF_INVALID = "PROOF_INVALID"


_VALID_TRANSITIONS = {
    (ProofState.PROOF_PENDING, ProofState.PROOF_GENERATING),
    (ProofState.PROOF_PENDING, ProofState.PROOF_FAILED),
    (ProofState.PROOF_PENDING, ProofState.PROOF_MISSING),
    (ProofState.PROOF_PENDING, ProofState.PROOF_INVALID),
    (ProofState.PROOF_GENERATING, ProofState.PROOF_GENERATED),
    (ProofState.PROOF_GENERATING, ProofState.PROOF_FAILED),
    (ProofState.PROOF_GENERATED, ProofState.PROOF_VERIFYING),
    (ProofState.PROOF_GENERATED, ProofState.PROOF_FAILED),
    (ProofState.PROOF_VERIFYING, ProofState.PROOF_VERIFIED),
    (ProofState.PROOF_VERIFYING, ProofState.PROOF_FAILED),
    (ProofState.PROOF_VERIFYING, ProofState.PROOF_INVALID),
    (ProofState.PROOF_VERIFYING, ProofState.PROOF_MISSING),
}


EXPECTED_FEATURE_DIM = 8


def check_ezkl_binary() -> bool:
    """Check if the ezkl utility is installed and executable in the environment path."""
    try:
        res = subprocess.run(["ezkl", "--version"], capture_output=True, text=True, timeout=10)
        return res.returncode == 0
    except Exception:
        return False


def get_circuit_input_dim() -> int:
    """Return the expected input dimension for the circuit."""
    return EXPECTED_FEATURE_DIM


def validate_proof_environment() -> Dict[str, Any]:
    """
    Validate the host environment before application startup or execution.
    Checks ezkl presence, required artifact existence, readability, and VK integrity.
    """
    report = {
        "valid": True,
        "ezkl_available": True,
        "missing_files": [],
        "unreadable_files": [],
        "vk_tampered": False,
        "errors": []
    }
    
    # 1. Verify EZKL command-line tool
    if not check_ezkl_binary():
        report["valid"] = False
        report["ezkl_available"] = False
        report["errors"].append("EZKL utility is not available or executable in the system path.")
        
    # 2. Verify existence and readability of required files
    for filename in REQUIRED_FILES:
        path = REPO_ROOT / filename
        if not path.exists():
            report["valid"] = False
            report["missing_files"].append(filename)
            report["errors"].append(f"Required artifact file '{filename}' is missing.")
        elif not os.access(path, os.R_OK):
            report["valid"] = False
            report["unreadable_files"].append(filename)
            report["errors"].append(f"Required artifact file '{filename}' exists but is not readable.")
            
    # 3. Verify vk.key cryptographic integrity
    vk_path = REPO_ROOT / "vk.key"
    if vk_path.exists() and os.access(vk_path, os.R_OK):
        try:
            with open(vk_path, "rb") as f:
                vk_hash = hashlib.sha256(f.read()).hexdigest()
            if vk_hash != TRUSTED_VK_HASH:
                report["valid"] = False
                report["vk_tampered"] = True
                report["errors"].append(f"vk.key integrity compromised! Got hash '{vk_hash}', expected '{TRUSTED_VK_HASH}'.")
        except Exception as e:
            report["valid"] = False
            report["errors"].append(f"Integrity check failed to read vk.key: {e}")
            
    return report


def validate_proof_artifacts(proof_path: str, witness_path: str = "witness.json") -> bool:
    """
    Verify the structural validity of ZK proof and witness artifacts.
    Checks json formats and required parameters to reject malformed files before verifier calls.
    """
    try:
        p_path = Path(proof_path)
        if not p_path.is_absolute():
            p_path = REPO_ROOT / p_path
            
        w_path = Path(witness_path)
        if not w_path.is_absolute():
            w_path = REPO_ROOT / w_path
        
        if not p_path.exists() or not w_path.exists():
            return False
            
        # Validate proof JSON structure
        with open(p_path, "r", encoding="utf-8") as f:
            proof_data = json.load(f)
        if not isinstance(proof_data, dict):
            return False
        if "instances" not in proof_data or "proof" not in proof_data:
            return False
        if not isinstance(proof_data["proof"], list) or len(proof_data["proof"]) == 0:
            return False
        if not isinstance(proof_data["instances"], list):
            return False
            
        # Validate witness JSON structure
        with open(w_path, "r", encoding="utf-8") as f:
            witness_data = json.load(f)
        if not isinstance(witness_data, dict):
            return False
        if "inputs" not in witness_data or "outputs" not in witness_data:
            return False
        if not isinstance(witness_data["inputs"], list) or not isinstance(witness_data["outputs"], list):
            return False
            
        return True
    except Exception:
        return False
