import os
import hashlib

VK_PATH = "vk.key"

# ⚠️ Generate once and hardcode this
TRUSTED_VK_HASH = "f519d8bddcf2801c194fb65e7d1ef628497462443e0891081e52c47bd99956e1"


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def verify_proof(proof_path):

    # 🔐 STEP 1: VERIFY VK INTEGRITY
    current_hash = sha256_file(VK_PATH)

    if current_hash != TRUSTED_VK_HASH:
        raise Exception("VK TAMPERING DETECTED")

    # 🔐 STEP 2: VERIFY PROOF
    res = os.system(
    f"ezkl verify "
    f"--proof-path {proof_path} "
    f"--vk-path {VK_PATH} "
    f"--srs-path kzg.srs"
)
    return res == 0