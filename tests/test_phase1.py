import sys
from pathlib import Path

# Add project root to sys.path to ensure imports work from within subdirectories
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from schema.intent_contract import IntentContract

contract = IntentContract(
    agent_name="TransactionAgent",
    user_task="Process order #123",
    allowed_tools=["proceed_transaction"],
    forbidden_tools=["send_email", "delete_database"],
)

print("Session ID:", contract.session_id)
print("Hash before sealing:", contract.intent_hash())

contract.seal()

print("Sealed Hash:", contract.intent_hash())

print("\nTrying to modify allowed_tools after sealing...")
print("Type of allowed_tools:", type(contract.allowed_tools))
try:
    contract.allowed_tools.append("send_email")  # Should fail
    print("WARNING: Modification succeeded, sealing failed!")
except Exception as e:
    print("SUCCESS: Modification blocked as expected:", e)
