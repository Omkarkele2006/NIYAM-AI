# schema/action_hash.py

import hashlib
import json


def compute_action_hash(tool_name: str, payload: dict) -> str:
    """
    Compute deterministic SHA-256 hash of tool call.
    """

    normalized = json.dumps(
        {
            "tool_name": tool_name,
            "payload": payload
        },
        sort_keys=True
    )

    return hashlib.sha256(normalized.encode()).hexdigest()