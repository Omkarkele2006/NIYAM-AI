import hashlib
import subprocess

VK_PATH = "vk.key"

TRUSTED_VK_HASH = "f519d8bddcf2801c194fb65e7d1ef628497462443e0891081e52c47bd99956e1"


def sha256_file(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def verify_proof(proof_path: str) -> bool:

    current_hash = sha256_file(VK_PATH)

    if current_hash != TRUSTED_VK_HASH:
        raise Exception("VK TAMPERING DETECTED")

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
