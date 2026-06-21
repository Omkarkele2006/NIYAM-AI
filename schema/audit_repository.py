import sqlite3
import json
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = REPO_ROOT / "audit.db"

class AuditRepository:
    """
    Database Abstraction Layer (AuditRepository) for SQLite audit logging.
    
    Handles table creation, indexing, event inserts, queries, metrics
    aggregations, and forensic-grade cryptographic chain validation.
    """
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path) if db_path else str(DEFAULT_DB_PATH)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    event_type TEXT,
                    status TEXT,
                    tool_name TEXT,
                    detail TEXT,
                    intent_hash TEXT,
                    action_hash TEXT,
                    proof_id TEXT,
                    verification INTEGER,
                    features TEXT,
                    reason TEXT,
                    execution_id TEXT,
                    state TEXT,
                    duration_ms REAL,
                    session_id TEXT,
                    prev_hash TEXT,
                    current_hash TEXT,
                    raw_data TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_events (session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_status ON audit_events (status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events (timestamp)")
            conn.commit()

    def get_last_hash(self) -> str:
        """Retrieve the last current_hash in the chain, returning '0' if empty."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT current_hash FROM audit_events WHERE current_hash IS NOT NULL ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return row["current_hash"] if row else "0"

    def insert_event(self, event: Dict[str, Any], recalculate_hashes: bool = True) -> Dict[str, Any]:
        """
        Insert an audit event into the database.
        
        Parameters
        ----------
        event : Dict[str, Any]
            The raw event record dictionary.
        recalculate_hashes : bool, optional
            If True, calculates prev_hash and current_hash dynamically.
            If False (e.g. for migrations), preserves existing hashes.
        """
        # Ensure timestamp exists
        if "timestamp" not in event:
            event["timestamp"] = datetime.utcnow().isoformat()

        # Handle cryptographic chain hashes
        if recalculate_hashes:
            prev = self.get_last_hash()
            event["prev_hash"] = prev
            
            # Make a copy without hashing keys to compute signature
            event_copy = event.copy()
            event_copy.pop("current_hash", None)
            event_copy.pop("log_hash", None)
            
            current_hash = hashlib.sha256((prev + json.dumps(event_copy)).encode()).hexdigest()
            event["current_hash"] = current_hash
            event["log_hash"] = current_hash
        else:
            prev = event.get("prev_hash")
            current_hash = event.get("current_hash") or event.get("log_hash")
            # Sync keys
            if current_hash:
                event["current_hash"] = current_hash
                event["log_hash"] = current_hash

        # Generate unique event_id if missing
        if "event_id" not in event:
            event["event_id"] = event.get("execution_id") or str(uuid.uuid4())
            # Ensure uniqueness if execution_id is reused across FSM transitions
            with self._get_connection() as conn:
                existing = conn.execute("SELECT id FROM audit_events WHERE event_id = ?", (event["event_id"],)).fetchone()
                if existing:
                    event["event_id"] = f"{event['event_id']}_{str(uuid.uuid4())[:8]}"

        # Map to columns
        event_id = event["event_id"]
        timestamp = event["timestamp"]
        event_type = event.get("event_type")
        status = event.get("status")
        tool_name = event.get("tool_name")
        detail = event.get("detail")
        intent_hash = event.get("intent_hash")
        action_hash = event.get("action_hash")
        
        proof_id = event.get("proof") or event.get("proof_id")
        
        verification_val = event.get("verification")
        if verification_val is True:
            verification = 1
        elif verification_val is False:
            verification = 0
        else:
            verification = None
            
        features = json.dumps(event.get("features")) if "features" in event else None
        reason = event.get("reason")
        execution_id = event.get("execution_id")
        state = event.get("state")
        duration_ms = event.get("duration_ms")
        session_id = event.get("session_id")

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO audit_events (
                    event_id, timestamp, event_type, status, tool_name, detail,
                    intent_hash, action_hash, proof_id, verification, features,
                    reason, execution_id, state, duration_ms, session_id,
                    prev_hash, current_hash, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id, timestamp, event_type, status, tool_name, detail,
                intent_hash, action_hash, proof_id, verification, features,
                reason, execution_id, state, duration_ms, session_id,
                prev, current_hash, json.dumps(event)
            ))
            conn.commit()
            
        return event

    def fetch_events(self, limit: Optional[int] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch all events with optional status filtering and limit constraints."""
        query = "SELECT raw_data FROM audit_events"
        params = []
        
        if status:
            query += " WHERE status = ?"
            params.append(status)
            
        query += " ORDER BY id ASC"
        
        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            
        events = [json.loads(row["raw_data"]) for row in rows]
        
        if limit is not None and limit >= 0:
            return events[-limit:]
            
        return events

    def fetch_recent_events(self, limit: int = 25) -> List[Dict[str, Any]]:
        """Fetch the most recent events."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT raw_data FROM audit_events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        # Return in ascending chronological order to match JSONL files
        events = [json.loads(row["raw_data"]) for row in rows]
        events.reverse()
        return events

    def count_metrics(self) -> Dict[str, Any]:
        """Aggregate high-level system audit counts using SQLite functions."""
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
            executed = conn.execute("SELECT COUNT(*) FROM audit_events WHERE status = 'EXECUTED'").fetchone()[0]
            blocked = conn.execute("SELECT COUNT(*) FROM audit_events WHERE status = 'BLOCKED'").fetchone()[0]
            errors = conn.execute("SELECT COUNT(*) FROM audit_events WHERE status = 'ERROR'").fetchone()[0]
            verified = conn.execute("SELECT COUNT(*) FROM audit_events WHERE verification = 1").fetchone()[0]
            
            # Fetch distinct session_ids
            sessions = conn.execute("SELECT COUNT(DISTINCT session_id) FROM audit_events WHERE session_id IS NOT NULL AND session_id != ''").fetchone()[0]
            
            # Fetch latest record
            latest_row = conn.execute("SELECT raw_data FROM audit_events ORDER BY id DESC LIMIT 1").fetchone()
            latest_record = json.loads(latest_row["raw_data"]) if latest_row else None
            
        return {
            "total_actions": total,
            "executed_actions": executed,
            "blocked_actions": blocked,
            "error_actions": errors,
            "verified_proofs": verified,
            "unique_sessions": sessions,
            "latest_record": latest_record,
            "latest_timestamp": latest_record.get("timestamp") if latest_record else None
        }

    def verify_chain(self) -> Dict[str, Any]:
        """
        Traverse the entire database to perform integrity and signature validation.
        
        Checks for chain breaks, record tampering, or missing documents.
        """
        with self._get_connection() as conn:
            rows = conn.execute("SELECT id, event_id, prev_hash, current_hash, raw_data FROM audit_events ORDER BY id ASC").fetchall()
            
        events_checked = 0
        broken_links = 0
        anomalies = []
        expected_prev_hash = None
        
        for row in rows:
            event_id = row["event_id"]
            stored_prev_hash = row["prev_hash"]
            stored_current_hash = row["current_hash"]
            
            try:
                event = json.loads(row["raw_data"])
            except Exception as e:
                anomalies.append(f"Row {row['id']} (event_id: {event_id}): JSON deserialization failure: {e}")
                broken_links += 1
                continue

            # Skip verification for unchained legacy rows
            if stored_prev_hash is None and stored_current_hash is None:
                continue
                
            events_checked += 1
            
            # 1. Check chain sequence linkage
            if stored_prev_hash == "0":
                # Genesis block of a new chain sequence session
                pass
            elif expected_prev_hash is not None:
                if stored_prev_hash != expected_prev_hash:
                    anomalies.append(
                        f"Row {row['id']} (event_id: {event_id}): Hash chain break. "
                        f"Expected prev_hash '{expected_prev_hash}', got '{stored_prev_hash}'."
                    )
                    broken_links += 1
            else:
                anomalies.append(
                    f"Row {row['id']} (event_id: {event_id}): Genesis prev_hash is not '0' (got '{stored_prev_hash}')."
                )
                broken_links += 1
                    
            # 2. Recompute hash signature
            event_copy = event.copy()
            event_copy.pop("current_hash", None)
            event_copy.pop("log_hash", None)
            event_copy.pop("event_id", None)
            event_copy["prev_hash"] = stored_prev_hash
            
            recomputed = hashlib.sha256((stored_prev_hash + json.dumps(event_copy)).encode()).hexdigest()
            if recomputed != stored_current_hash:
                anomalies.append(
                    f"Row {row['id']} (event_id: {event_id}): Record tampered. "
                    f"Recomputed current_hash '{recomputed}' != stored current_hash '{stored_current_hash}'."
                )
                broken_links += 1
                
            expected_prev_hash = stored_current_hash
            
        return {
            "valid": broken_links == 0,
            "events_checked": events_checked,
            "broken_links": broken_links,
            "anomalies": anomalies
        }

    def get_zkml_metrics(self) -> Dict[str, Any]:
        """
        Aggregate and compute health metrics of the ZK proof lifecycle.
        Reads all PROOF_ lifecycle events to evaluate success rates and average latencies.
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT event_type, raw_data FROM audit_events WHERE event_type LIKE 'PROOF_%'"
            ).fetchall()
            
        gen_success = 0
        gen_failed = 0
        ver_success = 0
        ver_failed = 0
        
        gen_latencies = []
        ver_latencies = []
        
        for row in rows:
            event_type = row["event_type"]
            try:
                data = json.loads(row["raw_data"])
            except Exception:
                continue
                
            if event_type == "PROOF_GENERATION_COMPLETED":
                gen_success += 1
                dur = data.get("generation_duration_ms")
                if dur is not None:
                    gen_latencies.append(dur)
            elif event_type == "PROOF_GENERATION_FAILED":
                gen_failed += 1
            elif event_type == "PROOF_VERIFICATION_COMPLETED":
                ver_success += 1
                dur = data.get("verification_duration_ms")
                if dur is not None:
                    ver_latencies.append(dur)
            elif event_type == "PROOF_VERIFICATION_FAILED":
                ver_failed += 1
                
        avg_gen = sum(gen_latencies) / len(gen_latencies) if gen_latencies else 0.0
        avg_ver = sum(ver_latencies) / len(ver_latencies) if ver_latencies else 0.0
        
        return {
            "proof_success_count": gen_success,
            "proof_failure_count": gen_failed,
            "verification_success_count": ver_success,
            "verification_failure_count": ver_failed,
            "average_proof_latency_ms": avg_gen,
            "average_verification_latency_ms": avg_ver
        }
