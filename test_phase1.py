
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
contract.allowed_tools.append("send_email")  # Should fail