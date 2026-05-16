import hashlib
import subprocess

VK_PATH = "vk.key"

# ⚠️ Generate once and hardcode this
TRUSTED_VK_HASH = "f519d8bddcf2801c194fb65e7d1ef628497462443e0891081e52c47bd99956e1"


def sha256_file(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def verify_proof(proof_path: str) -> bool:

    # 🔐 STEP 1: VERIFY VK INTEGRITY
    # Semantics unchanged: raises immediately if vk.key has been tampered with.
    current_hash = sha256_file(VK_PATH)

    if current_hash != TRUSTED_VK_HASH:
        raise Exception("VK TAMPERING DETECTED")

    # 🔐 STEP 2: VERIFY PROOF
    # Replaced os.system() with subprocess.run() using an argument list so that
    # no shell is involved — eliminates the shell-injection surface entirely.
    # The EZKL command arguments are identical to the original string form.
    # capture_output=True makes stderr available for debug printing without
    # altering the governance decision: only returncode determines the result.
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
        # Print stderr so operators can diagnose EZKL failures without changing
        # exception or return-value semantics seen by the interceptor.
        print("[verifier] ezkl verify stderr:", result.stderr.strip())

    return result.returncode == 0