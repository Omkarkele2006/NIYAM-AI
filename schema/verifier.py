import hashlib
import subprocess
from pathlib import Path
from schema.proof_lifecycle import validate_proof_artifacts

VK_PATH = "vk.key"
TRUSTED_VK_HASH = "f519d8bddcf2801c194fb65e7d1ef628497462443e0891081e52c47bd99956e1"


def sha256_file(path: str) -> str:
    """Compute the SHA-256 hash of a file."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def verify_proof(proof_path: str) -> bool:
    """
    Verify a ZK proof of execution using EZKL.
    
    Returns True if verification succeeds, False on failure or malformed artifacts (fail-closed).
    """
    # 1. Structural artifact checks
    if not validate_proof_artifacts(proof_path, "witness.json"):
        print("[verifier] ZK proof or witness artifacts are missing or structurally malformed.")
        return False

    # 2. Verification key integrity check
    try:
        current_hash = sha256_file(VK_PATH)
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
                "--proof-path", proof_path,
                "--vk-path", VK_PATH,
                "--srs-path", "kzg.srs",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("[verifier] ezkl verify stderr:", result.stderr.strip())
        return result.returncode == 0
    except Exception as e:
        print(f"[verifier] ezkl verify execution exception: {e}")
        return False
