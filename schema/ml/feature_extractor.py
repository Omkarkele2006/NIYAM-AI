import re

TOOL_MAP = {
    "proceed_transaction": 0,
    "send_email": 1,
    "read_file": 2,
    "write_file": 3,
    "delete_file": 4,
    "execute_shell": 5,
    "api_call": 6,
    "database_query": 7
}

HIGH_RISK = [
    "execute_shell",
    "delete_file"
]


HARM_PHRASES = [
    "ignore previous",
    "bypass",
    "override",
    "jailbreak",
    "without permission",
    "without consent",
    "without authorization",
    "secretly",
    "do not tell",
    "hack",
    "exploit",
    "malware",
    "disable safety"
]

INJECTION_PATTERNS = [
    r"drop\s+table",
    r"<script",
    r"\.\./",
    r"javascript:",
    r"exec\s*\(",
    r"rm\s+-rf",
]


def hash_to_float(h):
    return (int(h, 16) % 1000) / 1000


def contains_harmful_text(text):
    text = text.lower()
    return any(p in text for p in HARM_PHRASES)


def contains_injection(text):
    text = text.lower()

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text):
            return True

    return False


def extract_features(
    action_hash,
    intent_hash,
    tool_name,
    payload,
    contract
):

    payload_text = str(payload).lower()

    # F1 — Intent Hash
    f1 = hash_to_float(intent_hash)

    # F2 — Action Hash
    f2 = hash_to_float(action_hash)

    # F3 — Tool Encoding
    f3 = TOOL_MAP.get(tool_name, -1) / 10

    # F4 — Payload Size
    f4 = min(len(payload_text) / 500, 1.0)

    # F5 — High Risk Tool
    f5 = 1 if tool_name in HIGH_RISK else 0

    # F6 — Forbidden Tool
    f6 = 1 if tool_name in contract.forbidden_tools else 0

    # F7 — Harm / Jailbreak Signal
    f7 = 1 if contains_harmful_text(payload_text) else 0

    # F8 — Injection / Exploit Signal
    f8 = 1 if contains_injection(payload_text) else 0

    return [
        f1,
        f2,
        f3,
        f4,
        f5,
        f6,
        f7,
        f8
    ]