import json
import hashlib
from datetime import datetime
from pathlib import Path
from schema.audit_repository import AuditRepository

LOG_FILE = "audit_log.jsonl"

# Central AuditRepository instance
_repo = AuditRepository()

# Seed previous_hash from the last persisted SQLite database entry to maintain chain continuity
previous_hash: str = _repo.get_last_hash()


def compute_log_hash(prev: str, current: dict) -> str:
    """Compute the cryptographic hash signature for the current event log entry."""
    return hashlib.sha256((prev + json.dumps(current)).encode()).hexdigest()


def log_event(event: dict) -> None:
    """
    Log a structured governance or FSM event.
    
    Inserts the record into the SQLite database through the AuditRepository
    and maintains the legacy JSONLines log file for backward compatibility.
    """
    global previous_hash

    # Insert into SQLite database (handles prev_hash and current_hash auto-calculation)
    _repo.insert_event(event, recalculate_hashes=True)

    # Sync module-level previous_hash variable
    previous_hash = event.get("current_hash") or event.get("log_hash")

    # Double-write to legacy JSONL log file to maintain compatibility with legacy viewers
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except OSError:
        pass