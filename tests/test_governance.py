import sys
import json
from pathlib import Path

# Add project root to sys.path to ensure imports work from within subdirectories
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from schema.intent_contract import IntentContract
from schema.tool_gate import ToolAuthorityGate, GovernanceValidationError


def test_governance_suite():
    print("========================================")
    print("RUNNING GOVERNANCE VALIDATION TEST SUITE")
    print("========================================\n")

    # Set up mock contract
    contract = IntentContract(
        agent_name="TestGovernanceAgent",
        user_task="Auditing platform tool hardening",
        allowed_tools=[
            "proceed_transaction",
            "send_email",
            "read_file",
            "write_file"
        ],
        forbidden_tools=[
            "delete_file",
            "execute_shell",
            "api_call"
        ]
    )
    contract.seal()
    gate = ToolAuthorityGate(contract)

    # Track overall test results
    tests_run = 0
    tests_passed = 0

    def assert_validation_passes(tool_name: str, payload: dict, stage: str):
        nonlocal tests_run, tests_passed
        tests_run += 1
        print(f"[TEST {tests_run:02d}] {stage} - Tool: {tool_name} ... ", end="")
        try:
            gate.validate_tool(tool_name)
            gate.validate_schema(tool_name, payload)
            print("PASSED")
            tests_passed += 1
        except Exception as e:
            print(f"FAILED (Unexpectedly Blocked: {e})")

    def assert_validation_fails(tool_name: str, payload: dict, stage: str, expected_reason_substring: str):
        nonlocal tests_run, tests_passed
        tests_run += 1
        print(f"[TEST {tests_run:02d}] {stage} - Tool: {tool_name} ... ", end="")
        try:
            gate.validate_tool(tool_name)
            gate.validate_schema(tool_name, payload)
            print("FAILED (Allowed invalid payload!)")
        except GovernanceValidationError as e:
            # Parse structured error payload
            try:
                error_data = json.loads(str(e))
                assert error_data["tool"] == tool_name
                assert error_data["status"] == "BLOCKED"
                assert expected_reason_substring.lower() in error_data["reason"].lower()
                print("PASSED (Blocked correctly with structured error)")
                tests_passed += 1
            except Exception as assertion_err:
                print(f"FAILED (Structured error format assertion failed: {assertion_err})")
                print(f"  Got error payload: {str(e)}")
        except Exception as e:
            print(f"FAILED (Raised unexpected exception type: {type(e).__name__} - {e})")

    # ---------------------------------------------
    # 1. VALID CASES
    # ---------------------------------------------
    # Valid transaction
    assert_validation_passes(
        "proceed_transaction",
        {"amount": 250.50, "recipient": "user_alice", "note": "Invoice payment"},
        "VALID_CASE"
    )

    # Valid approved action (send_email)
    assert_validation_passes(
        "send_email",
        {"to": "user@domain.com", "data": "Hello world"},
        "VALID_CASE"
    )

    # Valid approved action (read_file with path)
    assert_validation_passes(
        "read_file",
        {"path": "configs/server_conf.json"},
        "VALID_CASE"
    )

    # ---------------------------------------------
    # 2. INVALID CASES
    # ---------------------------------------------
    # Missing required fields
    assert_validation_fails(
        "proceed_transaction",
        {"recipient": "user_bob"},
        "INVALID_CASE (missing field)",
        "'amount' is a required property"
    )

    # Wrong data types
    assert_validation_fails(
        "proceed_transaction",
        {"amount": "fifty_bucks", "recipient": "user_bob"},
        "INVALID_CASE (wrong data type)",
        "is not of type 'number'"
    )

    # Malformed email format
    assert_validation_fails(
        "send_email",
        {"to": "malformed_email_address", "data": "Test body"},
        "INVALID_CASE (malformed format)",
        "does not match"
    )

    # Forbidden tools check
    assert_validation_fails(
        "execute_shell",
        {"command": "whoami"},
        "INVALID_CASE (forbidden tool)",
        "is explicitly forbidden"
    )

    # Allowed by intent but missing schema (Default Deny test case)
    # We will simulate registering a tool in allowed list but not defining a schema
    contract_missing_schema = IntentContract(
        agent_name="MockAgent",
        user_task="Testing default deny",
        allowed_tools=["some_custom_tool"],
        forbidden_tools=[]
    )
    contract_missing_schema.seal()
    gate_missing_schema = ToolAuthorityGate(contract_missing_schema)
    
    tests_run += 1
    print(f"[TEST {tests_run:02d}] INVALID_CASE (missing schema) - Tool: some_custom_tool ... ", end="")
    try:
        gate_missing_schema.validate_tool("some_custom_tool")
        gate_missing_schema.validate_schema("some_custom_tool", {"param": 1})
        print("FAILED (Allowed tool with missing schema!)")
    except GovernanceValidationError as e:
        error_data = json.loads(str(e))
        if "no registered schema" in error_data["reason"].lower():
            print("PASSED (Blocked missing schema default-deny correctly)")
            tests_passed += 1
        else:
            print(f"FAILED (Unexpected block reason: {error_data['reason']})")
    except Exception as e:
        print(f"FAILED (Raised unexpected error: {e})")

    # ---------------------------------------------
    # 3. SECURITY CASES
    # ---------------------------------------------
    # Extra unexpected fields (additionalProperties: False check)
    assert_validation_fails(
        "proceed_transaction",
        {"amount": 100.0, "recipient": "user_alice", "extra_hacking_field": "injected"},
        "SECURITY_CASE (unexpected fields)",
        "Additional properties are not allowed"
    )

    # Oversized payload checking (maxLength check)
    assert_validation_fails(
        "send_email",
        {"to": "target@domain.com", "data": "A" * 20000},  # maxLength is 10000
        "SECURITY_CASE (oversized payload)",
        "is too long"
    )

    print("\n----------------------------------------")
    print(f"GOVERNANCE SUITE RUN COMPLETED: {tests_passed}/{tests_run} PASSED")
    print("----------------------------------------")

    if tests_passed != tests_run:
        sys.exit(1)


if __name__ == "__main__":
    test_governance_suite()
