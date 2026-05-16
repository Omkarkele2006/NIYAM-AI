from schema.intent_contract import IntentContract
from schema.control_flow import ControlFlowIntegrity
from schema.tool_gate import ToolAuthorityGate
from schema.interceptor import intercept_execution


def execute_tool(tool_name, payload):
    print(f"[Execution] Tool executed: {tool_name}")
    print(f"[Execution] Payload: {payload}")
    return "SUCCESS"


# ===============================
# CREATE INTENT CONTRACT
# ===============================
contract = IntentContract(
    agent_name="TransactionAgent",
    user_task="Process order #123",
    allowed_tools=[
        "proceed_transaction",
        "read_file",
        "write_file",
        "api_call"
    ],
    forbidden_tools=[
        "send_email",
        "execute_shell",
        "delete_file"
    ]
)

contract.seal()

# ===============================
# SAFE EXECUTION TEST
# ===============================
print("\n==============================")
print("SAFE EXECUTION TEST")
print("==============================")

cfi_safe = ControlFlowIntegrity(["proceed_transaction"] * 5)
gate = ToolAuthorityGate(contract)

for i in range(3):
    try:
        result = intercept_execution(
            tool_name="proceed_transaction",
            payload={
                "amount": 100 + i,
                "recipient": "user1"
            },
            contract=contract,
            cfi=cfi_safe,
            gate=gate,
            execute_func=execute_tool
        )
        print("Result:", result)

    except Exception as e:
        print("Execution Blocked (SAFE TEST):", e)


# ===============================
# ATTACK TEST 1: FORBIDDEN TOOL
# ===============================
print("\n==============================")
print("ATTACK TEST: FORBIDDEN TOOL (EMAIL)")
print("==============================")

cfi_attack1 = ControlFlowIntegrity(["send_email"])

try:
    intercept_execution(
        tool_name="send_email",
        payload={"to": "hacker@email.com"},
        contract=contract,
        cfi=cfi_attack1,
        gate=gate,
        execute_func=execute_tool
    )
except Exception as e:
    print("Execution Blocked:", e)


# ===============================
# ATTACK TEST 2: LARGE TRANSACTION
# ===============================
print("\n==============================")
print("ATTACK TEST: LARGE TRANSACTION")
print("==============================")

cfi_attack2 = ControlFlowIntegrity(["proceed_transaction"])

try:
    intercept_execution(
        tool_name="proceed_transaction",
        payload={
            "amount": 1000000,
            "recipient": "user1"
        },
        contract=contract,
        cfi=cfi_attack2,
        gate=gate,
        execute_func=execute_tool
    )
except Exception as e:
    print("Execution Blocked:", e)