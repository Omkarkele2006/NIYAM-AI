import unittest
import json
import sqlite3
import uuid
import os
from pathlib import Path
import sys

# Ensure project root is in sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from schema.audit_repository import AuditRepository
from schema.audit_logger import log_event
from test_sandbox import test_sandbox_suite

class TestAuditSqlite(unittest.TestCase):
    def setUp(self):
        self.test_db = f"test_audit_{uuid.uuid4().hex[:8]}.db"
        self.repo = AuditRepository(self.test_db)

    def tearDown(self):
        if os.path.exists(self.test_db):
            try:
                os.unlink(self.test_db)
            except OSError:
                pass

    # ==========================================
    # FUNCTIONAL TESTS
    # ==========================================
    def test_event_insertion_and_retrieval(self):
        # Insert event
        event_dict = {
            "session_id": "test_session_1",
            "tool_name": "proceed_transaction",
            "status": "EXECUTED",
            "timestamp": "2026-06-21T12:00:00Z"
        }
        inserted = self.repo.insert_event(event_dict, recalculate_hashes=True)
        
        self.assertIsNotNone(inserted.get("current_hash"))
        self.assertEqual(inserted.get("prev_hash"), "0")
        
        # Retrieve event
        events = self.repo.fetch_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["session_id"], "test_session_1")
        self.assertEqual(events[0]["tool_name"], "proceed_transaction")
        self.assertEqual(events[0]["status"], "EXECUTED")

    def test_ordering_and_filtering(self):
        # Insert 3 events
        self.repo.insert_event({"session_id": "s1", "status": "EXECUTED"}, recalculate_hashes=True)
        self.repo.insert_event({"session_id": "s2", "status": "BLOCKED"}, recalculate_hashes=True)
        self.repo.insert_event({"session_id": "s3", "status": "EXECUTED"}, recalculate_hashes=True)
        
        # Verify ordering (ASC by ID)
        events = self.repo.fetch_events()
        self.assertEqual(events[0]["session_id"], "s1")
        self.assertEqual(events[1]["session_id"], "s2")
        self.assertEqual(events[2]["session_id"], "s3")
        
        # Verify status filtering
        executed_events = self.repo.fetch_events(status="EXECUTED")
        self.assertEqual(len(executed_events), 2)
        self.assertEqual(executed_events[0]["session_id"], "s1")
        self.assertEqual(executed_events[1]["session_id"], "s3")
        
        # Verify limit constraints
        recent = self.repo.fetch_events(limit=2)
        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0]["session_id"], "s2")
        self.assertEqual(recent[1]["session_id"], "s3")

    # ==========================================
    # SECURITY TESTS
    # ==========================================
    def test_chain_verification_success(self):
        # Insert sequential chained events
        self.repo.insert_event({"session_id": "s1", "status": "EXECUTED"}, recalculate_hashes=True)
        self.repo.insert_event({"session_id": "s2", "status": "BLOCKED"}, recalculate_hashes=True)
        self.repo.insert_event({"session_id": "s3", "status": "EXECUTED"}, recalculate_hashes=True)
        
        report = self.repo.verify_chain()
        self.assertTrue(report["valid"])
        self.assertEqual(report["events_checked"], 3)
        self.assertEqual(report["broken_links"], 0)

    def test_modified_record_detection(self):
        # Insert sequential chained events
        self.repo.insert_event({"session_id": "s1", "status": "EXECUTED"}, recalculate_hashes=True)
        self.repo.insert_event({"session_id": "s2", "status": "BLOCKED"}, recalculate_hashes=True)
        
        # Check chain is initially valid
        self.assertTrue(self.repo.verify_chain()["valid"])
        
        # Manually tamper with the database record using raw SQLite
        conn = sqlite3.connect(self.test_db)
        # Modify the raw_data and columns of s1
        conn.execute("UPDATE audit_events SET status = 'EXECUTED_TAMPERED', detail = 'Tampered' WHERE id = 1")
        # Also modify raw_data dict status to mismatch computed hash
        row = conn.execute("SELECT raw_data FROM audit_events WHERE id = 1").fetchone()
        event_dict = json.loads(row[0])
        event_dict["status"] = "EXECUTED_TAMPERED"
        conn.execute("UPDATE audit_events SET raw_data = ? WHERE id = 1", (json.dumps(event_dict),))
        conn.commit()
        conn.close()
        
        # Verify chain detect tampering
        report = self.repo.verify_chain()
        self.assertFalse(report["valid"])
        self.assertGreater(report["broken_links"], 0)
        self.assertTrue(any("tampered" in a.lower() for a in report["anomalies"]))

    def test_deleted_record_detection(self):
        # Insert sequential chained events
        self.repo.insert_event({"session_id": "s1", "status": "EXECUTED"}, recalculate_hashes=True)
        self.repo.insert_event({"session_id": "s2", "status": "BLOCKED"}, recalculate_hashes=True)
        self.repo.insert_event({"session_id": "s3", "status": "EXECUTED"}, recalculate_hashes=True)
        
        # Manually delete event 2 using raw SQLite
        conn = sqlite3.connect(self.test_db)
        conn.execute("DELETE FROM audit_events WHERE id = 2")
        conn.commit()
        conn.close()
        
        # Verify chain detect break (s3's prev_hash won't match s1's current_hash)
        report = self.repo.verify_chain()
        self.assertFalse(report["valid"])
        self.assertGreater(report["broken_links"], 0)
        self.assertTrue(any("break" in a.lower() for a in report["anomalies"]))

    # ==========================================
    # MIGRATION TESTS
    # ==========================================
    def test_migration_and_hash_preservation(self):
        # Create a mock jsonl file
        mock_jsonl = f"mock_log_{uuid.uuid4().hex[:8]}.jsonl"
        events_to_write = [
            {"session_id": "legacy_s1", "status": "SAFE", "timestamp": "2026-01-01T00:00:00Z"},
            {"session_id": "legacy_s2", "status": "BLOCKED", "timestamp": "2026-01-02T00:00:00Z", "prev_hash": "0", "log_hash": "hash123"}
        ]
        with open(mock_jsonl, "w", encoding="utf-8") as f:
            for ev in events_to_write:
                f.write(json.dumps(ev) + "\n")
                
        # Import legacy events using the repository directly
        for ev in events_to_write:
            self.repo.insert_event(ev, recalculate_hashes=False)
            
        # Verify events imported successfully and hashes/timestamps were preserved
        imported = self.repo.fetch_events()
        self.assertEqual(len(imported), 2)
        self.assertEqual(imported[0]["session_id"], "legacy_s1")
        self.assertEqual(imported[0]["timestamp"], "2026-01-01T00:00:00Z")
        self.assertIsNone(imported[0].get("prev_hash"))
        
        self.assertEqual(imported[1]["session_id"], "legacy_s2")
        self.assertEqual(imported[1]["prev_hash"], "0")
        self.assertEqual(imported[1]["log_hash"], "hash123")
        
        # Cleanup mock file
        if os.path.exists(mock_jsonl):
            os.unlink(mock_jsonl)

    # ==========================================
    # REGRESSION TESTS
    # ==========================================
    def test_governance_and_sandbox_regression(self):
        # Execute sandbox test suite directly to guarantee regression security
        print("\n[Regression Test] Executing sandbox test suite to ensure execution containment works...")
        try:
            test_sandbox_suite()
        except SystemExit as exc:
            self.assertEqual(exc.code, 0, "Sandbox execution test suite failed")

if __name__ == '__main__':
    unittest.main()
