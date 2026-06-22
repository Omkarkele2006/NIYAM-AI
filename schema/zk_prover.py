import json
import subprocess
import os
import time
from pathlib import Path
from schema.audit_logger import log_event

REPO_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = "input.json"
WITNESS_FILE = "witness.json"
PROOF_FILE = "proof.json"

RETAIN_EPHEMERAL_ARTIFACTS = True
_retain_flag = os.environ.get("NIYAM_RETAIN_EPHEMERAL_ARTIFACTS")
if _retain_flag is not None:
    RETAIN_EPHEMERAL_ARTIFACTS = _retain_flag.lower() in ("true", "1", "yes")

_execution_durations = {}

def get_execution_durations(execution_id: str) -> dict | None:
    """Retrieve and pop the execution durations for the given execution_id."""
    return _execution_durations.pop(execution_id, None)


def generate_proof(features: list, execution_id: str | None = None, session_id: str | None = None) -> str | None:
    """
    Generate a zero-knowledge proof of execution using EZKL.
    
    Returns the path to the proof file on success, or None on failure (fail-closed).
    Deletes stale or partial artifacts on failure.
    """
    # 1. Resolve paths
    if execution_id:
        exec_dir = REPO_ROOT / "artifacts" / "executions" / execution_id
        exec_dir.mkdir(parents=True, exist_ok=True)
        input_file = exec_dir / "input.json"
        witness_file = exec_dir / "witness.json"
        proof_file = exec_dir / "proof.json"
    else:
        input_file = REPO_ROOT / "input.json"
        witness_file = REPO_ROOT / "witness.json"
        proof_file = REPO_ROOT / "proof.json"

    # Helper function to remove files on failure
    def cleanup_on_failure(cleanup_input=False, cleanup_witness=False, cleanup_proof=False):
        for path, active in [(input_file, cleanup_input), (witness_file, cleanup_witness), (proof_file, cleanup_proof)]:
            if active and path.exists():
                try:
                    path.unlink()
                except OSError:
                    pass

    # 2. Write features to input.json
    try:
        with open(input_file, "w") as f:
            json.dump(
                {"input_data": [features]},
                f
            )
    except OSError as e:
        print(f"[zk_prover] Failed to write input_file: {e}")
        return None

    # 3. Generate witness (120s timeout)
    t_start_witness = time.monotonic()
    try:
        res1 = subprocess.run(
            [
                "ezkl", "gen-witness",
                "--data", str(input_file),
                "--compiled-circuit", str(REPO_ROOT / "circuit.ezkl"),
                "--output", str(witness_file),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if res1.returncode != 0:
            print("[zk_prover] gen-witness stderr:", res1.stderr.strip())
            cleanup_on_failure(cleanup_input=True, cleanup_witness=True)
            return None
    except subprocess.TimeoutExpired as e:
        print(f"[zk_prover] gen-witness execution timed out: {e}")
        log_event({
            "session_id": session_id or "",
            "execution_id": execution_id or "",
            "event_type": "WITNESS_GENERATION_TIMEOUT",
            "status": "BLOCKED",
            "reason": "Witness generation timed out after 120s"
        })
        cleanup_on_failure(cleanup_input=True, cleanup_witness=True)
        return None
    except Exception as e:
        print(f"[zk_prover] gen-witness execution exception: {e}")
        cleanup_on_failure(cleanup_input=True, cleanup_witness=True)
        return None
    t_witness_dur = (time.monotonic() - t_start_witness) * 1000

    # 4. Generate proof (300s timeout)
    t_start_proof = time.monotonic()
    try:
        res2 = subprocess.run(
            [
                "ezkl", "prove",
                "--witness", str(witness_file),
                "--compiled-circuit", str(REPO_ROOT / "circuit.ezkl"),
                "--pk-path", str(REPO_ROOT / "pk.key"),
                "--proof-path", str(proof_file),
                "--srs-path", str(REPO_ROOT / "kzg.srs"),
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if res2.returncode != 0:
            print("[zk_prover] prove stderr:", res2.stderr.strip())
            cleanup_on_failure(cleanup_input=True, cleanup_witness=True, cleanup_proof=True)
            return None
    except subprocess.TimeoutExpired as e:
        print(f"[zk_prover] prove execution timed out: {e}")
        log_event({
            "session_id": session_id or "",
            "execution_id": execution_id or "",
            "event_type": "PROOF_GENERATION_TIMEOUT",
            "status": "BLOCKED",
            "reason": "Proof generation timed out after 300s"
        })
        cleanup_on_failure(cleanup_input=True, cleanup_witness=True, cleanup_proof=True)
        return None
    except Exception as e:
        print(f"[zk_prover] prove execution exception: {e}")
        cleanup_on_failure(cleanup_input=True, cleanup_witness=True, cleanup_proof=True)
        return None
    t_proof_dur = (time.monotonic() - t_start_proof) * 1000

    if execution_id:
        _execution_durations[execution_id] = {
            "witness_generation_ms": t_witness_dur,
            "proof_generation_ms": t_proof_dur
        }

    # Optional: cleanup ephemeral artifacts if retention policy is disabled
    if not RETAIN_EPHEMERAL_ARTIFACTS:
        cleanup_on_failure(cleanup_input=True, cleanup_witness=True)

    return str(proof_file)


def _unlink_stale_files(witness: bool = False, proof: bool = False) -> None:
    """Helper to remove stale or partially written proof artifacts (maintained for backward compatibility)."""
    if witness:
        stale_witness = REPO_ROOT / WITNESS_FILE
        if stale_witness.exists():
            try:
                stale_witness.unlink()
            except OSError:
                pass
    if proof:
        stale_proof = REPO_ROOT / PROOF_FILE
        if stale_proof.exists():
            try:
                stale_proof.unlink()
            except OSError:
                pass

