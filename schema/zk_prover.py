import json
import subprocess
from pathlib import Path


INPUT_FILE = "input.json"
WITNESS_FILE = "witness.json"
PROOF_FILE = "proof.json"


def generate_proof(features: list) -> str | None:


    with open(INPUT_FILE, "w") as f:
        json.dump(
            {"input_data": [features]},
            f
        )

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

        stale_witness = Path(WITNESS_FILE)
        if stale_witness.exists():
            stale_witness.unlink()

        return None

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
