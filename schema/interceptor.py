import time
import os
from pathlib import Path
from schema.action_hash import compute_action_hash
from schema.audit_logger import log_event
from schema.zk_prover import generate_proof, get_execution_durations
from schema.verifier import verify_proof, sha256_file
from schema.ml.feature_extractor import extract_features
from schema.orchestration.execution_runtime import (
    GovernedExecutionContext,
    GovernedExecutionRuntime,
    derive_execution_id,
)
from schema.proof_lifecycle import validate_proof_environment, get_circuit_input_dim

# Startup Validation Layer
_env_report = validate_proof_environment()
if not _env_report["valid"]:
    print(f"[*] zkML Environment Validation: FAILED - {'; '.join(_env_report['errors'])}")
    try:
        log_event({
            "session_id": "STARTUP",
            "event_type": "PROOF_ENVIRONMENT_INVALID",
            "status": "ERROR",
            "detail": f"Environment validation failed: {'; '.join(_env_report['errors'])}"
        })
    except Exception:
        pass
else:
    print("[*] zkML Environment Validation: SUCCESS")


class InterceptionBlocked(Exception):
    pass


# Module-level runtime instance.  Stateless between calls — safe to reuse.
_runtime = GovernedExecutionRuntime(
    emit=lambda event: log_event(event.to_dict())
)


def intercept_execution(tool_name, payload, contract, cfi, gate, execute_func):
    action_hash = compute_action_hash(tool_name, payload)
    intent_hash = contract.intent_hash()

    print("\n[Interceptor] Tool:", tool_name)
    print("[Interceptor] ActionHash:", action_hash)

    # 1. Startup environment validation check (Fail-Closed Enforcement)
    if not _env_report["valid"]:
        log_event({
            "session_id": contract.session_id,
            "intent_hash": intent_hash,
            "action_hash": action_hash,
            "tool_name": tool_name,
            "event_type": "PROOF_ENVIRONMENT_INVALID",
            "status": "BLOCKED",
            "reason": f"EZKL environment check failed: {'; '.join(_env_report['errors'])}"
        })
        log_event({
            "session_id": contract.session_id,
            "intent_hash": intent_hash,
            "action_hash": action_hash,
            "tool_name": tool_name,
            "event_type": "PROOF_EXECUTION_BLOCKED",
            "status": "BLOCKED",
            "reason": "EZKL environment check failed at startup"
        })
        raise InterceptionBlocked(f"EZKL environment is invalid: {'; '.join(_env_report['errors'])}")

    try:
        # STEP 1: Control Flow
        cfi.validate_step(tool_name)

        # STEP 2: Tool Gate
        gate.validate_tool(tool_name)
        gate.validate_schema(tool_name, payload)

        # STEP 3: Feature Extraction (ML INPUT)
        features = extract_features(
            action_hash,
            intent_hash,
            tool_name,
            payload,
            contract
        )

        # STEP 4: Feature Dimension Validation
        expected_dim = get_circuit_input_dim()
        if expected_dim is not None and len(features) != expected_dim:
            log_event({
                "session_id": contract.session_id,
                "intent_hash": intent_hash,
                "action_hash": action_hash,
                "tool_name": tool_name,
                "event_type": "FEATURE_DIMENSION_MISMATCH",
                "status": "BLOCKED",
                "reason": f"Feature dimension mismatch: got {len(features)}, expected {expected_dim}"
            })
            log_event({
                "session_id": contract.session_id,
                "intent_hash": intent_hash,
                "action_hash": action_hash,
                "tool_name": tool_name,
                "event_type": "PROOF_EXECUTION_BLOCKED",
                "status": "BLOCKED",
                "reason": f"Feature dimension mismatch: got {len(features)}, expected {expected_dim}"
            })
            raise Exception(f"Feature dimension mismatch: got {len(features)}, expected {expected_dim}")

        # Pre-derive a unique execution_id
        execution_id = derive_execution_id(
            action_hash=action_hash,
            intent_hash=intent_hash,
            proof_path="ephemeral_isolated",
            timestamp_ns=time.time_ns()
        )

        # -- PROOF LIFECYCLE: GENERATION STARTED --
        log_event({
            "session_id": contract.session_id,
            "intent_hash": intent_hash,
            "action_hash": action_hash,
            "tool_name": tool_name,
            "event_type": "PROOF_GENERATION_STARTED",
            "status": "PROCESSING",
        })

        t_start_gen = time.monotonic()
        
        # STEP 5: Generate zk proof
        proof_path = generate_proof(features, execution_id=execution_id, session_id=contract.session_id)
        
        t_dur_gen = (time.monotonic() - t_start_gen) * 1000  # ms

        if not proof_path:
            log_event({
                "session_id": contract.session_id,
                "intent_hash": intent_hash,
                "action_hash": action_hash,
                "tool_name": tool_name,
                "event_type": "PROOF_GENERATION_FAILED",
                "status": "BLOCKED",
                "reason": "Proof generation failed",
                "generation_duration_ms": t_dur_gen,
            })
            log_event({
                "session_id": contract.session_id,
                "intent_hash": intent_hash,
                "action_hash": action_hash,
                "tool_name": tool_name,
                "event_type": "PROOF_EXECUTION_BLOCKED",
                "status": "BLOCKED",
                "reason": "Proof generation failed"
            })
            raise Exception("Proof generation failed")

        proof_size = os.path.getsize(proof_path) if os.path.exists(proof_path) else 0

        # Retrieve individual witness & proof generation times
        durations = get_execution_durations(execution_id) or {}
        witness_generation_ms = durations.get("witness_generation_ms")
        proof_generation_ms = durations.get("proof_generation_ms")

        # Compute artifact hashes
        proof_hash = sha256_file(proof_path) if os.path.exists(proof_path) else None
        proof_dir = Path(proof_path).parent if proof_path else None
        witness_path = str(proof_dir / "witness.json") if proof_dir else None
        input_path = str(proof_dir / "input.json") if proof_dir else None
        witness_hash = sha256_file(witness_path) if (witness_path and os.path.exists(witness_path)) else None
        input_hash = sha256_file(input_path) if (input_path and os.path.exists(input_path)) else None

        log_event({
            "session_id": contract.session_id,
            "intent_hash": intent_hash,
            "action_hash": action_hash,
            "tool_name": tool_name,
            "event_type": "PROOF_GENERATION_COMPLETED",
            "status": "PROCESSING",
            "generation_duration_ms": t_dur_gen,
            "proof_size_bytes": proof_size,
            "proof_hash": proof_hash,
            "proof_archive_path": str(Path(proof_path).resolve()) if proof_path else None,
        })

        # -- PROOF LIFECYCLE: VERIFICATION STARTED --
        log_event({
            "session_id": contract.session_id,
            "intent_hash": intent_hash,
            "action_hash": action_hash,
            "tool_name": tool_name,
            "event_type": "PROOF_VERIFICATION_STARTED",
            "status": "PROCESSING",
        })

        t_start_ver = time.monotonic()
        
        # STEP 6: Verify proof
        verified = verify_proof(proof_path, witness_path=witness_path)
        
        t_dur_ver = (time.monotonic() - t_start_ver) * 1000  # ms

        if not verified:
            log_event({
                "session_id": contract.session_id,
                "intent_hash": intent_hash,
                "action_hash": action_hash,
                "tool_name": tool_name,
                "event_type": "PROOF_VERIFICATION_FAILED",
                "status": "BLOCKED",
                "reason": "Proof verification failed",
                "verification_duration_ms": t_dur_ver,
            })
            log_event({
                "session_id": contract.session_id,
                "intent_hash": intent_hash,
                "action_hash": action_hash,
                "tool_name": tool_name,
                "event_type": "PROOF_EXECUTION_BLOCKED",
                "status": "BLOCKED",
                "reason": "Proof verification failed"
            })
            raise Exception("Proof verification failed")

        log_event({
            "session_id": contract.session_id,
            "intent_hash": intent_hash,
            "action_hash": action_hash,
            "tool_name": tool_name,
            "event_type": "PROOF_VERIFICATION_COMPLETED",
            "status": "PROCESSING",
            "verification_duration_ms": t_dur_ver,
            "verification": True,
            "proof_hash": proof_hash,
            "witness_hash": witness_hash,
        })

        # STEP 7: GOVERNED EXECUTION — timeout-enforced, proof-bound runtime
        exec_context = GovernedExecutionContext(
            execution_id=execution_id,
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

        # STEP 8: GOVERNED EXECUTION COMPLETED (LOG SUCCESS WITH METRICS)
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
            "proof_hash": proof_hash,
            "witness_hash": witness_hash,
            "input_hash": input_hash,
            "proof_archive_path": str(Path(proof_path).resolve()) if proof_path else None,
            "witness_generation_ms": witness_generation_ms,
            "proof_generation_ms": proof_generation_ms,
            "verification_ms": t_dur_ver,
            "total_proof_pipeline_ms": t_dur_gen + t_dur_ver,
        })

        return result

    except Exception as e:
        # ALERT SYSTEM (FR21)
        print("\n[SECURITY ALERT]")
        print("Blocked Action:", tool_name)
        print("Reason:", str(e))

        # Extract explainability details if available
        policy_val = getattr(e, "policy", None)
        rule_val = getattr(e, "rule", None)
        reason_val = getattr(e, "reason", str(e))

        # Log event
        log_payload = {
            "session_id": contract.session_id,
            "intent_hash": intent_hash,
            "action_hash": action_hash,
            "tool_name": tool_name,
            "status": "BLOCKED",
            "reason": reason_val
        }
        if policy_val:
            log_payload["policy"] = policy_val
        if rule_val:
            log_payload["rule"] = rule_val

        log_event(log_payload)

        raise InterceptionBlocked(str(e))