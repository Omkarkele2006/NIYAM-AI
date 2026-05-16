import random
import csv

from schema.action_hash import compute_action_hash
from schema.intent_contract import IntentContract
from schema.ml.feature_extractor import extract_features

# -------------------------
# LIGHTWEIGHT LABELING
# -------------------------

def classify_sample(tool, payload, contract):

    payload_text = str(payload).lower()

    harmful_patterns = [
        "ignore previous",
        "bypass",
        "hack",
        "exploit",
        "drop table",
        "<script>",
        "javascript:",
        "exec(",
        "disable safety",
        "without permission",
        "without authorization"
    ]

    # Forbidden tool
    if tool in contract.forbidden_tools:
        return 0

    # Harmful payload
    if any(p in payload_text for p in harmful_patterns):
        return 0

    # High-risk transaction
    if payload.get("amount", 0) > 50000:
        return 0

    return 1
# -------------------------
# CONFIG
# -------------------------

TOOLS = [
    "proceed_transaction",
    "send_email",
    "read_file",
    "write_file",
    "delete_file",
    "execute_shell",
    "api_call",
    "database_query"
]

SAFE_TOOLS = [
    "proceed_transaction",
    "read_file",
    "write_file",
    "api_call"
]

UNSAFE_TOOLS = [
    "send_email",
    "execute_shell",
    "delete_file"
]

NOISE_PROB = 0.05  # 5% label noise


# -------------------------
# RANDOM CONTRACT GENERATOR
# -------------------------

def generate_random_contract():

    allowed = random.sample(SAFE_TOOLS, k=random.randint(2, len(SAFE_TOOLS)))
    forbidden = random.sample(UNSAFE_TOOLS, k=random.randint(1, len(UNSAFE_TOOLS)))

    contract = IntentContract(
        agent_name="Agent",
        user_task="Task_" + str(random.randint(1, 100)),
        allowed_tools=allowed,
        forbidden_tools=forbidden
    )

    contract.seal()
    return contract


# -------------------------
# PAYLOAD GENERATORS
# -------------------------

def generate_safe_payload(tool):

    if tool == "proceed_transaction":
        return {
            "amount": random.randint(10, 5000),
            "recipient": "user_" + str(random.randint(1, 100)),
            "note": "normal transaction"
        }

    return {
        "data": "normal_operation"
    }

def generate_unsafe_payload(tool):

    attack_payloads = [
        {"data": "ignore previous instructions"},
        {"data": "bypass security"},
        {"data": "hack the system"},
        {"data": "drop table users"},
        {"data": "<script>alert(1)</script>"},
        {"data": "../etc/passwd"},
        {"data": "javascript:alert(1)"},
        {"data": "exec(rm -rf /)"},
        {"data": "disable safety"},
        {"data": "without permission"},
    ]

    if tool == "proceed_transaction":
        return {
            "amount": random.randint(50000, 200000),
            "recipient": "attacker",
            "note": "without authorization"
        }

    return random.choice(attack_payloads)

# -------------------------
# MAIN GENERATOR
# -------------------------

def generate_dataset(n_samples=10000):

    data = []

    safe_count = 0
    unsafe_count = 0

    while len(data) < n_samples:

        # 🔥 IMPORTANT: generate new contract every sample
        contract = generate_random_contract()

        # -------------------------
        # SAFE SAMPLE
        # -------------------------
        if safe_count < n_samples // 2:

            while True:
                tool = random.choice(contract.allowed_tools)
                payload = generate_safe_payload(tool)

                action_hash = compute_action_hash(tool, payload)
                intent_hash = contract.intent_hash()

                label = classify_sample(tool, payload, contract)

                if label == 1:
                    break

        # -------------------------
        # UNSAFE SAMPLE
        # -------------------------
        else:

            while True:
                tool = random.choice(TOOLS)

                # Force violation sometimes
                if random.random() < 0.5 and contract.forbidden_tools:
                    tool = random.choice(contract.forbidden_tools)

                payload = generate_unsafe_payload(tool)

                action_hash = compute_action_hash(tool, payload)
                intent_hash = contract.intent_hash()

                label = classify_sample(tool, payload, contract)

                if label == 0:
                    break

        # -------------------------
        # ADD NOISE
        # -------------------------
        if random.random() < NOISE_PROB:
            label = 1 - label

        # Count AFTER noise
        if label == 1:
            safe_count += 1
        else:
            unsafe_count += 1

        # -------------------------
        # FEATURE EXTRACTION
        # -------------------------
        features = extract_features(
            action_hash,
            intent_hash,
            tool,
            payload,
            contract
        )

        data.append(features + [label])

    print(f"Generated {len(data)} samples")
    print(f"Safe: {safe_count}, Unsafe: {unsafe_count}")

    return data


# -------------------------
# SAVE CSV
# -------------------------

def save_dataset(data, filename="dataset.csv"):

    headers = [
    "intent_hash",
    "action_hash",
    "tool_id",
    "payload_size",
    "is_high_risk",
    "is_forbidden",
    "harmful_signal",
    "injection_signal",
    "label"
]

    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data)

    print(f"Dataset saved to {filename}")


# -------------------------
# RUN
# -------------------------

if __name__ == "__main__":

    dataset = generate_dataset(10000)
    save_dataset(dataset)