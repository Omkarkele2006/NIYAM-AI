import hashlib
import subprocess
from pathlib import Path
from schema.proof_lifecycle import validate_proof_artifacts

REPO_ROOT = Path(__file__).resolve().parents[1]
VK_PATH = REPO_ROOT / "vk.key"
TRUSTED_VK_HASH = "f519d8bddcf2801c194fb65e7d1ef628497462443e0891081e52c47bd99956e1"


def sha256_file(path: str) -> str:
    """Compute the SHA-256 hash of a file."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def verify_proof(proof_path: str, witness_path: str | None = None) -> bool:
    """
    Verify a ZK proof of execution using EZKL.
    
    Returns True if verification succeeds, False on failure or malformed artifacts (fail-closed).
    """
    # 1. Structural artifact checks
    actual_witness = witness_path if witness_path is not None else str(REPO_ROOT / "witness.json")
    if not validate_proof_artifacts(proof_path, actual_witness):
        print("[verifier] ZK proof or witness artifacts are missing or structurally malformed.")
        return False

    # 2. Verification key integrity check
    try:
        current_hash = sha256_file(str(VK_PATH))
        if current_hash != TRUSTED_VK_HASH:
            raise Exception("VK TAMPERING DETECTED")
    except Exception as e:
        print(f"[verifier] VK integrity validation error: {e}")
        return False

    # 3. Cryptographic verification execution
    try:
        result = subprocess.run(
            [
                "ezkl", "verify",
                "--proof-path", str(proof_path),
                "--vk-path", str(VK_PATH),
                "--srs-path", str(REPO_ROOT / "kzg.srs"),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            print("[verifier] ezkl verify stderr:", result.stderr.strip())
        return result.returncode == 0
    except subprocess.TimeoutExpired as e:
        print(f"[verifier] ezkl verify timed out: {e}")
        return False
    except Exception as e:
        print(f"[verifier] ezkl verify execution exception: {e}")
        return False
