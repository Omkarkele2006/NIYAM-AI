import os
import json

INPUT_FILE = "input.json"
WITNESS_FILE = "witness.json"
PROOF_FILE = "proof.json"


def generate_proof(features):

    # -------------------------
    # STEP 1: SAVE INPUT
    # -------------------------

    with open(INPUT_FILE, "w") as f:
        json.dump(
            {"input_data": [features]},
            f
        )

    # -------------------------
    # STEP 2: GENERATE WITNESS
    # -------------------------

    witness_cmd = (
        f"ezkl gen-witness "
        f"--data {INPUT_FILE} "
        f"--compiled-circuit circuit.ezkl "
        f"--output {WITNESS_FILE}"
    )

    res1 = os.system(witness_cmd)

    if res1 != 0:
        return None

    # -------------------------
    # STEP 3: GENERATE PROOF
    # -------------------------

    proof_cmd = (
        f"ezkl prove "
        f"--witness {WITNESS_FILE} "
        f"--compiled-circuit circuit.ezkl "
        f"--pk-path pk.key "
        f"--proof-path {PROOF_FILE} "
        f"--srs-path kzg.srs"
    )

    res2 = os.system(proof_cmd)

    if res2 != 0:
        return None

    return PROOF_FILE