import json
import hashlib
from datetime import datetime

LOG_FILE = "audit_log.jsonl"

previous_hash = "0"


def compute_log_hash(prev, current):
    return hashlib.sha256((prev + json.dumps(current)).encode()).hexdigest()


def log_event(event: dict):
    global previous_hash

    event["timestamp"] = datetime.utcnow().isoformat()

    # Add chaining
    event["prev_hash"] = previous_hash

    log_hash = compute_log_hash(previous_hash, event)
    event["log_hash"] = log_hash

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(event) + "\n")

    previous_hash = log_hash