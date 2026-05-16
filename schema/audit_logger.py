import json
import hashlib
from datetime import datetime
from pathlib import Path


LOG_FILE = "audit_log.jsonl"


def _bootstrap_chain_hash(log_file: str) -> str:
    """
    Seed the in-memory chain hash from the last successfully written log entry.

    Without this, every process restart resets previous_hash to "0", silently
    breaking chain continuity even though the on-disk log is intact.  Reading
    the last non-empty line and extracting its log_hash restores the chain
    exactly where it left off.  If the file does not exist or no valid record
    is found, "0" is returned — identical to the original cold-start behavior.
    """
    path = Path(log_file)
    if not path.exists():
        return "0"

    last_valid_hash = "0"
    try:
        with path.open("r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    candidate = record.get("log_hash")
                    if isinstance(candidate, str) and candidate:
                        last_valid_hash = candidate
                except json.JSONDecodeError:
                    # Partial write from a prior crash — skip and keep last good hash.
                    continue
    except OSError:
        # File exists but is unreadable — fall back to cold-start value.
        return "0"

    return last_valid_hash


# Seed from the last persisted entry so the chain is continuous across restarts.
previous_hash: str = _bootstrap_chain_hash(LOG_FILE)


def compute_log_hash(prev: str, current: dict) -> str:
    return hashlib.sha256((prev + json.dumps(current)).encode()).hexdigest()


def log_event(event: dict) -> None:
    global previous_hash

    event["timestamp"] = datetime.utcnow().isoformat()

    # Add chaining
    event["prev_hash"] = previous_hash

    log_hash = compute_log_hash(previous_hash, event)
    event["log_hash"] = log_hash

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(event) + "\n")

    previous_hash = log_hash