# schema/judge.py

class JudgeModel:
    """
    zkML-based Judge placeholder.

    NOTE:
    This class is intentionally minimal because
    safety enforcement is now done via:

        Feature Extraction → zk Proof → Verification

    This prevents any non-verifiable logic from influencing execution.
    """

    def classify(self, *args, **kwargs):
        raise Exception(
            "JudgeModel is deprecated. Use zkML pipeline (feature_extractor + zk_prover + verifier)."
        )