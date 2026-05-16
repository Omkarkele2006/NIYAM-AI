from schema.action_hash import compute_action_hash
from schema.audit_logger import log_event
from schema.zk_prover import generate_proof
from schema.verifier import verify_proof
from schema.ml.feature_extractor import extract_features


class InterceptionBlocked(Exception):
    pass


def intercept_execution(tool_name, payload, contract, cfi, gate, execute_func):

    action_hash = compute_action_hash(tool_name, payload)
    intent_hash = contract.intent_hash()

    print("\n[Interceptor] Tool:", tool_name)
    print("[Interceptor] ActionHash:", action_hash)

    try:
        # STEP 1: Control Flow
        cfi.validate_step(tool_name)

        # STEP 2: Tool Gate
        gate.validate_tool(tool_name)

        # STEP 3: Feature Extraction (ML INPUT)
        features = extract_features(
            action_hash,
            intent_hash,
            tool_name,
            payload,
            contract
        )

        # STEP 4: (OPTIONAL LOCAL CHECK — REMOVE LATER)
        # You can skip judge.py completely now

        # STEP 5: Generate zk proof
        proof_path = generate_proof(features)

        if not proof_path:
            raise Exception("Proof generation failed")

        # STEP 6: Verify proof
        verified = verify_proof(proof_path)

        if not verified:
            raise Exception("Proof verification failed")

        # STEP 7: EXECUTE
        result = execute_func(tool_name, payload)

        # STEP 8: LOG SUCCESS
        log_event({
            "session_id": contract.session_id,
            "intent_hash": intent_hash,
            "action_hash": action_hash,
            "tool_name": tool_name,
            "features": features,
            "proof": proof_path,
            "verification": True,
            "status": "EXECUTED"
        })

        return result

    except Exception as e:

        # 🚨 ALERT SYSTEM (FR21)
        print("\n🚨 SECURITY ALERT 🚨")
        print("Blocked Action:", tool_name)
        print("Reason:", str(e))

        # Log event
        log_event({
            "session_id": contract.session_id,
            "intent_hash": intent_hash,
            "action_hash": action_hash,
            "tool_name": tool_name,
            "status": "BLOCKED",
            "reason": str(e)
        })

        raise InterceptionBlocked(str(e))