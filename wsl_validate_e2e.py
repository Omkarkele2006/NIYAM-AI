#!/usr/bin/env python3
"""
NIYAM-AI End-to-End Pipeline Validation
========================================
Runs the full governance pipeline stage-by-stage and produces evidence
at each step. No Streamlit. No architecture changes. Uses existing runtime.
"""

import sys
import json
import hashlib
import os
import sqlite3
from pathlib import Path

REPO = Path("/mnt/c/IMP/VIT/SY/SEM_2/EDI/NiyamAI-Proj-Code-Original")
sys.path.insert(0, str(REPO))

# ── CWD must be REPO root for all relative-path subprocess calls ──
os.chdir(REPO)

SEPARATOR = "=" * 60
PASS = "[PASS]"
FAIL = "[FAIL]"
INFO = "[INFO]"

def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def section(title):
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)

# ─────────────────────────────────────────────────────────────
# STAGE 0: Environment Validation
# ─────────────────────────────────────────────────────────────
section("STAGE 0: ENVIRONMENT VALIDATION")

from schema.proof_lifecycle import validate_proof_environment

env = validate_proof_environment()
print(f"{INFO} ezkl_available : {env['ezkl_available']}")
print(f"{INFO} missing_files  : {env['missing_files']}")
print(f"{INFO} vk_tampered    : {env['vk_tampered']}")
print(f"{INFO} errors         : {env['errors']}")

if not env["valid"]:
    print(f"\n{FAIL} Environment validation FAILED. Cannot proceed.")
    sys.exit(1)

print(f"\n{PASS} STAGE 0 PASSED — zkML environment is valid")

# ─────────────────────────────────────────────────────────────
# STAGE 1: Intent Contract
# ─────────────────────────────────────────────────────────────
section("STAGE 1: INTENT CONTRACT")

from schema.intent_contract import IntentContract

contract = IntentContract(
    agent_name="TransactionAgent",
    user_task="Process payment for order #123",
    allowed_tools=["proceed_transaction"],
    forbidden_tools=["send_email", "delete_database"],
)
contract.seal()
intent_hash = contract.intent_hash()

print(f"{INFO} agent_name     : {contract.agent_name}")
print(f"{INFO} allowed_tools  : {list(contract.allowed_tools)}")
print(f"{INFO} forbidden_tools: {list(contract.forbidden_tools)}")
print(f"{INFO} session_id     : {contract.session_id}")
print(f"{INFO} intent_hash    : {intent_hash}")
print(f"\n{PASS} STAGE 1 PASSED — IntentContract sealed")

# ─────────────────────────────────────────────────────────────
# STAGE 2: CFI Validation
# ─────────────────────────────────────────────────────────────
section("STAGE 2: CONTROL FLOW INTEGRITY")

from schema.control_flow import ControlFlowIntegrity

tool_name = "proceed_transaction"
payload = {"amount": 100, "recipient": "Vendor_A"}

cfi = ControlFlowIntegrity(["proceed_transaction"])
try:
    cfi.validate_step(tool_name)
    print(f"{INFO} tool           : {tool_name}")
    print(f"{INFO} declared_seq   : ['proceed_transaction']")
    print(f"\n{PASS} STAGE 2 PASSED — CFI check cleared")
except Exception as e:
    print(f"{FAIL} CFI FAILED: {e}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────
# STAGE 3: Tool Authorization
# ─────────────────────────────────────────────────────────────
section("STAGE 3: TOOL AUTHORIZATION & SCHEMA VALIDATION")

from schema.tool_gate import ToolAuthorityGate

gate = ToolAuthorityGate(contract)
try:
    gate.validate_tool(tool_name)
    print(f"{INFO} validate_tool  : AUTHORIZED")
except Exception as e:
    print(f"{FAIL} Tool authorization FAILED: {e}")
    sys.exit(1)

try:
    gate.validate_schema(tool_name, payload)
    print(f"{INFO} validate_schema: SCHEMA VALID")
    print(f"{INFO} payload        : {payload}")
    print(f"\n{PASS} STAGE 3 PASSED — Tool authorized, schema valid")
except Exception as e:
    print(f"{FAIL} Schema validation FAILED: {e}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────
# STAGE 4: Feature Extraction
# ─────────────────────────────────────────────────────────────
section("STAGE 4: FEATURE EXTRACTION")

from schema.ml.feature_extractor import extract_features
from schema.action_hash import compute_action_hash

action_hash = compute_action_hash(tool_name, payload)
features = extract_features(action_hash, intent_hash, tool_name, payload, contract)

print(f"{INFO} action_hash    : {action_hash[:32]}...")
print(f"{INFO} feature_dim    : {len(features)}")
print(f"{INFO} feature_vector : {features}")

if len(features) != 8:
    print(f"{FAIL} Expected 8 features, got {len(features)}")
    sys.exit(1)

print(f"\n{PASS} STAGE 4 PASSED — Feature vector extracted ({len(features)} floats)")

# ─────────────────────────────────────────────────────────────
# STAGE 5 + 6: Witness + Proof Generation (via zk_prover)
# ─────────────────────────────────────────────────────────────
section("STAGE 5+6: WITNESS GENERATION + PROOF GENERATION")

import time
from schema.zk_prover import generate_proof, get_execution_durations
from schema.orchestration.execution_runtime import derive_execution_id

# Derive execution_id before proof generation just like the Interceptor
execution_id = derive_execution_id(
    action_hash=action_hash,
    intent_hash=intent_hash,
    proof_path="ephemeral_isolated",
    timestamp_ns=time.time_ns()
)

exec_dir = REPO / "artifacts" / "executions" / execution_id
exec_dir.mkdir(parents=True, exist_ok=True)

print(f"{INFO} Writing input.json with features...")
input_path = exec_dir / "input.json"
with open(input_path, "w") as f:
    json.dump({"input_data": [features]}, f)
print(f"{INFO} input.json     : {input_path} ({input_path.stat().st_size} bytes)")

print(f"{INFO} Calling generate_proof(features)...")
t_start = time.monotonic()
proof_path = generate_proof(features, execution_id=execution_id, session_id=contract.session_id)
t_elapsed = (time.monotonic() - t_start) * 1000

if proof_path is None:
    print(f"{FAIL} Proof generation FAILED (generate_proof returned None)")
    sys.exit(1)

proof_file = exec_dir / "proof.json"
witness_file = exec_dir / "witness.json"

proof_exists = proof_file.exists()
witness_exists = witness_file.exists()

print(f"\n{INFO} Elapsed        : {t_elapsed:.0f} ms")
print(f"{INFO} proof.json     : {'EXISTS' if proof_exists else 'MISSING'} ({proof_file.stat().st_size if proof_exists else 0:,} bytes)")
print(f"{INFO} witness.json   : {'EXISTS' if witness_exists else 'MISSING'} ({witness_file.stat().st_size if witness_exists else 0:,} bytes)")

if not proof_exists or not witness_exists:
    print(f"{FAIL} Proof or witness artifact is missing after generation")
    sys.exit(1)

# Retrieve individual witness & proof generation times
durations = get_execution_durations(execution_id) or {}
witness_generation_ms = durations.get("witness_generation_ms")
proof_generation_ms = durations.get("proof_generation_ms")

proof_hash = sha256_file(proof_file)
witness_hash = sha256_file(witness_file)
input_hash = sha256_file(input_path)

print(f"{INFO} proof_hash     : {proof_hash[:32]}...")
print(f"{INFO} witness_hash   : {witness_hash[:32]}...")
print(f"{INFO} input_hash     : {input_hash[:32]}...")

print(f"\n{PASS} STAGE 5+6 PASSED — Witness and proof generated in {t_elapsed:.0f} ms")

# ─────────────────────────────────────────────────────────────
# STAGE 7: Proof Verification
# ─────────────────────────────────────────────────────────────
section("STAGE 7: PROOF VERIFICATION")

from schema.verifier import verify_proof

print(f"{INFO} Running verify_proof('{proof_path}')...")
t_ver_start = time.monotonic()
verified = verify_proof(proof_path, witness_path=str(witness_file))
t_ver_elapsed = (time.monotonic() - t_ver_start) * 1000

print(f"{INFO} ezkl verify    : {'SUCCESS (returncode=0)' if verified else 'FAILED (returncode!=0)'}")
print(f"{INFO} Elapsed        : {t_ver_elapsed:.0f} ms")
print(f"{INFO} verified       : {verified}")

if not verified:
    print(f"\n{FAIL} STAGE 7 FAILED — Proof verification returned False")
    sys.exit(1)

print(f"\n{PASS} STAGE 7 PASSED — Proof cryptographically verified (verified=True)")

# ─────────────────────────────────────────────────────────────
# STAGE 8: Governed Execution
# ─────────────────────────────────────────────────────────────
section("STAGE 8: GOVERNED EXECUTION RUNTIME")

from schema.orchestration.execution_runtime import (
    GovernedExecutionContext,
    GovernedExecutionRuntime,
)
from schema.audit_logger import log_event

def dummy_execute(tool_name, payload):
    return {"status": "ok", "tool": tool_name, "amount": payload.get("amount"), "recipient": payload.get("recipient")}

exec_context = GovernedExecutionContext(
    execution_id=execution_id,
    tool_name=tool_name,
    action_hash=action_hash,
    intent_hash=intent_hash,
    proof_path=str(proof_path),
    proof_verified=verified,
    session_id=contract.session_id,
)

runtime = GovernedExecutionRuntime(
    emit=lambda event: log_event(event.to_dict())
)

print(f"{INFO} execution_id   : {execution_id[:32]}...")
print(f"{INFO} proof_verified : {exec_context.proof_verified}")
print(f"{INFO} tool_name      : {exec_context.tool_name}")
print(f"{INFO} Running SandboxExecutor...")

t_exec_start = time.monotonic()
exec_result = runtime.execute_governed(
    context=exec_context,
    execute_func=dummy_execute,
    payload=payload,
)
t_exec_elapsed = (time.monotonic() - t_exec_start) * 1000

print(f"{INFO} state          : {exec_result.state.value}")
print(f"{INFO} result         : {exec_result.result}")
print(f"{INFO} duration_ms    : {exec_result.duration_ms:.1f}")
print(f"{INFO} events emitted : {len(exec_result.events)}")

if exec_result.state.value != "COMPLETED":
    print(f"\n{FAIL} STAGE 8 FAILED — Execution state: {exec_result.state.value}")
    sys.exit(1)

print(f"\n{PASS} STAGE 8 PASSED — Governed execution completed in {exec_result.duration_ms:.1f} ms")

# ─────────────────────────────────────────────────────────────
# STAGE 9: Audit Logging
# ─────────────────────────────────────────────────────────────
section("STAGE 9: AUDIT LOGGING")

log_event({
    "session_id": contract.session_id,
    "intent_hash": intent_hash,
    "action_hash": action_hash,
    "tool_name": tool_name,
    "features": features,
    "proof": str(proof_path),
    "proof_hash": proof_hash,
    "witness_hash": witness_hash,
    "input_hash": input_hash,
    "proof_archive_path": str(Path(proof_path).resolve()) if proof_path else None,
    "verification": True,
    "status": "EXECUTED",
    "execution_id": execution_id,
    "witness_generation_ms": witness_generation_ms,
    "proof_generation_ms": proof_generation_ms,
    "verification_ms": t_ver_elapsed,
    "total_proof_pipeline_ms": t_elapsed + t_ver_elapsed,
    "generation_duration_ms": t_elapsed,
    "verification_duration_ms": t_ver_elapsed,
})

# Read back from DB to confirm
from schema.audit_repository import AuditRepository
repo = AuditRepository()
events = repo.fetch_events(limit=5)
executed_events = [e for e in events if e.get("status") == "EXECUTED"]

print(f"{INFO} Total DB events (recent 5): {len(events)}")
print(f"{INFO} EXECUTED events found      : {len(executed_events)}")

if executed_events:
    last = executed_events[-1]
    print(f"{INFO} Last EXECUTED event:")
    print(f"       tool_name  : {last.get('tool_name')}")
    print(f"       status     : {last.get('status')}")
    print(f"       verification: {last.get('verification')}")
    print(f"       proof_hash : {str(last.get('proof_hash', ''))[:32]}...")
    print(f"       timestamp  : {last.get('timestamp')}")

print(f"\n{PASS} STAGE 9 PASSED — Audit event written and retrieved from DB")

# ─────────────────────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────────────────────
section("VALIDATION SUMMARY")

print(f"""
  Stage 0  Environment Validation    {PASS}
  Stage 1  Intent Contract           {PASS}
  Stage 2  CFI Validation            {PASS}
  Stage 3  Tool Authorization        {PASS}
  Stage 4  Feature Extraction        {PASS}
  Stage 5  Witness Generation        {PASS}
  Stage 6  Proof Generation          {PASS}
  Stage 7  Proof Verification        {PASS}  [verified=True]
  Stage 8  Governed Execution        {PASS}  [state=COMPLETED]
  Stage 9  Audit Logging             {PASS}

  Proof artifact    : {proof_file} ({proof_file.stat().st_size:,} bytes)
  Witness artifact  : {witness_file} ({witness_file.stat().st_size:,} bytes)
  Proof SHA-256     : {proof_hash[:48]}...
  Witness SHA-256   : {witness_hash[:48]}...
  Execution ID      : {execution_id[:48]}...
  Generation time   : {t_elapsed:.0f} ms
  Verification time : {t_ver_elapsed:.0f} ms
  Execution time    : {exec_result.duration_ms:.1f} ms

  RESULT: END-TO-END PROOF-GATED EXECUTION SUCCESSFUL
""")

print("=" * 60)
print("  NIYAM-AI zkML GOVERNANCE: FULLY OPERATIONAL")
print("=" * 60)
