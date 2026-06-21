from schema.action_hash import compute_action_hash
from schema.audit_logger import log_event
from schema.zk_prover import generate_proof
from schema.verifier import verify_proof
from schema.ml.feature_extractor import extract_features
from schema.orchestration.execution_runtime import (
    GovernedExecutionContext,
    GovernedExecutionRuntime,
    derive_execution_id,
)


class InterceptionBlocked(Exception):
    pass


# Module-level runtime instance.  Stateless between calls — safe to reuse.
_runtime = GovernedExecutionRuntime()


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


        # STEP 5: Generate zk proof
        proof_path = generate_proof(features)

        if not proof_path:
            raise Exception("Proof generation failed")

        # STEP 6: Verify proof
        verified = verify_proof(proof_path)

        if not verified:
            raise Exception("Proof verification failed")

        # STEP 7: GOVERNED EXECUTION — timeout-enforced, proof-bound runtime
        exec_context = GovernedExecutionContext(
            execution_id=derive_execution_id(
                action_hash=action_hash,
                intent_hash=intent_hash,
                proof_path=str(proof_path),
            ),
            tool_name=tool_name,
            action_hash=action_hash,
            intent_hash=intent_hash,
            proof_path=str(proof_path),
            proof_verified=verified,
            session_id=contract.session_id,
        )

        exec_result = _runtime.execute_governed(
            context=exec_context,
            execute_func=execute_func,
            payload=payload,
        )

        result = exec_result.result

        # STEP 8: LOG SUCCESS
        log_event({
            "session_id": contract.session_id,
            "intent_hash": intent_hash,
            "action_hash": action_hash,
            "tool_name": tool_name,
            "features": features,
            "proof": proof_path,
            "verification": True,
            "status": "EXECUTED",
            "execution_id": exec_context.execution_id,
        })

        return result

    except Exception as e:

        # ALERT SYSTEM (FR21)
        print("\n[SECURITY ALERT]")
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