import json
import subprocess
from pathlib import Path

INPUT_FILE = "input.json"
WITNESS_FILE = "witness.json"
PROOF_FILE = "proof.json"


def generate_proof(features: list) -> str | None:
    """
    Generate a zero-knowledge proof of execution using EZKL.
    
    Returns the path to the proof file on success, or None on failure (fail-closed).
    Deletes stale or partial artifacts on failure.
    """
    try:
        with open(INPUT_FILE, "w") as f:
            json.dump(
                {"input_data": [features]},
                f
            )
    except OSError as e:
        print(f"[zk_prover] Failed to write INPUT_FILE: {e}")
        return None

    try:
        res1 = subprocess.run(
            [
                "ezkl", "gen-witness",
                "--data", INPUT_FILE,
                "--compiled-circuit", "circuit.ezkl",
                "--output", WITNESS_FILE,
            ],
            capture_output=True,
            text=True,
        )
        if res1.returncode != 0:
            print("[zk_prover] gen-witness stderr:", res1.stderr.strip())
            _unlink_stale_files(witness=True)
            return None
    except Exception as e:
        print(f"[zk_prover] gen-witness execution exception: {e}")
        _unlink_stale_files(witness=True)
        return None

    try:
        res2 = subprocess.run(
            [
                "ezkl", "prove",
                "--witness", WITNESS_FILE,
                "--compiled-circuit", "circuit.ezkl",
                "--pk-path", "pk.key",
                "--proof-path", PROOF_FILE,
                "--srs-path", "kzg.srs",
            ],
            capture_output=True,
            text=True,
        )
        if res2.returncode != 0:
            print("[zk_prover] prove stderr:", res2.stderr.strip())
            _unlink_stale_files(proof=True)
            return None
    except Exception as e:
        print(f"[zk_prover] prove execution exception: {e}")
        _unlink_stale_files(proof=True)
        return None

    return PROOF_FILE


def _unlink_stale_files(witness: bool = False, proof: bool = False) -> None:
    """Helper to remove stale or partially written proof artifacts."""
    if witness:
        stale_witness = Path(WITNESS_FILE)
        if stale_witness.exists():
            try:
                stale_witness.unlink()
            except OSError:
                pass
    if proof:
        stale_proof = Path(PROOF_FILE)
        if stale_proof.exists():
            try:
                stale_proof.unlink()
            except OSError:
                pass
