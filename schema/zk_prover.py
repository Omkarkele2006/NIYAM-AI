import json
import subprocess
from pathlib import Path


INPUT_FILE = "input.json"
WITNESS_FILE = "witness.json"
PROOF_FILE = "proof.json"


def generate_proof(features: list) -> str | None:

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
    # Replaced os.system() with subprocess.run() using an argument list.
    # No shell=True — eliminates shell injection surface.
    # EZKL arguments are identical to the original string form.
    # capture_output=True captures stderr for debug visibility.

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

        # Remove any stale witness artifact so it cannot be mistaken for a
        # valid witness on the next run through the interceptor.
        stale_witness = Path(WITNESS_FILE)
        if stale_witness.exists():
            stale_witness.unlink()

        return None

    # -------------------------
    # STEP 3: GENERATE PROOF
    # -------------------------

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

        # Remove any partially written proof artifact so the verifier cannot
        # receive a corrupt or stale proof.json from a prior successful run.
        stale_proof = Path(PROOF_FILE)
        if stale_proof.exists():
            stale_proof.unlink()

        return None

    return PROOF_FILE