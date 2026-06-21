import unittest
import os
import sys
import uuid
import sqlite3
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from schema.audit_repository import AuditRepository
from schema.policy import Policy, PolicyRepository, compare_versions
from schema.governance_service import (
    get_dashboard_overview_metrics,
    load_audit_logs
)

class TestDashboardGovernance(unittest.TestCase):
    def setUp(self):
        # Clear Streamlit caches to prevent cross-test pollution
        get_dashboard_overview_metrics.clear()
        load_audit_logs.clear()

        # Unique test database for each test run to isolate test side-effects
        self.test_db = f"test_dashboard_{uuid.uuid4().hex[:8]}.db"
        self.db_path = REPO_ROOT / self.test_db
        
        # Patch AuditRepository.__init__ to redirect all DB connections to test_db
        self.original_audit_init = AuditRepository.__init__
        test_db_path = self.db_path
        def patched_audit_init(audit_self, db_path=None):
            audit_self.db_path = str(test_db_path)
            audit_self._init_db()
        AuditRepository.__init__ = patched_audit_init
        
        self.repo = AuditRepository()

        # Set up temporary directory for PolicyRepository
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_dir_path = Path(self.temp_dir.name)
        
        # Patch PolicyRepository.__init__ to redirect all policy files to the temp dir
        self.original_policy_init = PolicyRepository.__init__
        def patched_policy_init(policy_self, directory=None):
            policy_self.directory = temp_dir_path
            policy_self.directory.mkdir(parents=True, exist_ok=True)
        PolicyRepository.__init__ = patched_policy_init
        
        self.policy_repo = PolicyRepository()

    def tearDown(self):
        # Clear caches again
        get_dashboard_overview_metrics.clear()
        load_audit_logs.clear()

        # Restore original init methods
        AuditRepository.__init__ = self.original_audit_init
        PolicyRepository.__init__ = self.original_policy_init
        
        if self.db_path.exists():
            try:
                self.db_path.unlink()
            except OSError:
                pass
        self.temp_dir.cleanup()

    def test_get_dashboard_overview_metrics(self):
        # 1. Setup policies in policy repo
        policy_data_1 = {
            "policy_id": "test_finance",
            "version": "1.0.0",
            "status": "active",
            "created_at": "2026-06-21T12:00:00Z",
            "description": "Finance version 1",
            "allowed_tools": ["proceed_transaction"],
            "forbidden_tools": ["execute_shell"],
            "constraints": {},
            "metadata": {}
        }
        policy_data_2 = {
            "policy_id": "test_finance",
            "version": "1.1.0",
            "status": "draft",
            "created_at": "2026-06-21T13:00:00Z",
            "description": "Finance version 1.1",
            "allowed_tools": ["proceed_transaction", "read_file"],
            "forbidden_tools": ["execute_shell"],
            "constraints": {},
            "metadata": {}
        }
        p1 = self.policy_repo.load_policy_from_dict(policy_data_1)
        p2 = self.policy_repo.load_policy_from_dict(policy_data_2)
        
        self.policy_repo.save_policy(p1)
        self.policy_repo.save_policy(p2)

        # 2. Setup mock audit events
        # Policy validations and rejections
        self.repo.insert_event({"event_type": "POLICY_VALIDATED", "status": "SUCCESS"}, recalculate_hashes=True)
        self.repo.insert_event({"event_type": "POLICY_VALIDATED", "status": "SUCCESS"}, recalculate_hashes=True)
        self.repo.insert_event({"event_type": "POLICY_REJECTED", "status": "FAILED"}, recalculate_hashes=True)

        # Executions: success, blocked, failed, timed_out
        self.repo.insert_event({"tool_name": "t1", "status": "EXECUTED", "state": "SUCCESS"}, recalculate_hashes=True)
        self.repo.insert_event({"tool_name": "t2", "status": "BLOCKED", "state": "BLOCKED"}, recalculate_hashes=True)
        self.repo.insert_event({"tool_name": "t3", "status": "FAILED", "state": "FAILED"}, recalculate_hashes=True)
        self.repo.insert_event({"tool_name": "t4", "status": "FAILED", "state": "TIMED_OUT"}, recalculate_hashes=True)
        self.repo.insert_event({"tool_name": "t5", "status": "FAILED", "state": "TERMINATED"}, recalculate_hashes=True)

        # zkML counts
        self.repo.insert_event({"event_type": "PROOF_GENERATION_COMPLETED", "status": "SUCCESS"}, recalculate_hashes=True)
        self.repo.insert_event({"event_type": "PROOF_GENERATION_FAILED", "status": "FAILED"}, recalculate_hashes=True)
        self.repo.insert_event({"event_type": "PROOF_VERIFICATION_COMPLETED", "status": "SUCCESS"}, recalculate_hashes=True)
        self.repo.insert_event({"event_type": "PROOF_VERIFICATION_FAILED", "status": "FAILED"}, recalculate_hashes=True)

        # Fetch overview metrics through governance service
        metrics = get_dashboard_overview_metrics()

        # Assert correct calculation of policy metadata
        self.assertEqual(metrics["active_policies"], 1)
        self.assertEqual(metrics["total_policy_versions"], 2)
        # 2 validation success, 1 rejection = 3 total. Success rate = 2/3 * 100 = 66.666...%
        self.assertAlmostEqual(metrics["policy_validation_success_rate"], 66.66666666666667)
        self.assertEqual(metrics["policy_rejections"], 1)

        # Assert executions counts
        self.assertEqual(metrics["successful_executions"], 1)
        self.assertEqual(metrics["blocked_executions"], 1)
        self.assertEqual(metrics["failed_executions"], 1)
        self.assertEqual(metrics["timed_out_executions"], 2)  # TIMED_OUT + TERMINATED

        # Assert proof/verification counts
        self.assertEqual(metrics["proof_success_count"], 1)
        self.assertEqual(metrics["proof_failure_count"], 1)
        self.assertEqual(metrics["verification_success_count"], 1)
        self.assertEqual(metrics["verification_failure_count"], 1)

        # Assert audit chain integrity
        self.assertEqual(metrics["chain_status"], "VALID")
        self.assertEqual(metrics["broken_links_count"], 0)
        self.assertIsNotNone(metrics["last_integrity_check"])

    def test_compare_versions(self):
        policy_data_1 = {
            "policy_id": "test_finance",
            "version": "1.0.0",
            "status": "active",
            "created_at": "2026-06-21T12:00:00Z",
            "description": "Finance version 1",
            "allowed_tools": ["proceed_transaction", "read_file"],
            "forbidden_tools": ["execute_shell"],
            "constraints": {"max_amount": 1000},
            "metadata": {}
        }
        policy_data_2 = {
            "policy_id": "test_finance",
            "version": "1.1.0",
            "status": "inactive",
            "created_at": "2026-06-21T13:00:00Z",
            "description": "Finance version 1.1 modified",
            "allowed_tools": ["proceed_transaction", "write_file"],
            "forbidden_tools": ["execute_shell", "delete_file"],
            "constraints": {"max_amount": 5000, "new_constraint": True},
            "metadata": {}
        }
        p1 = self.policy_repo.load_policy_from_dict(policy_data_1)
        p2 = self.policy_repo.load_policy_from_dict(policy_data_2)

        diff = compare_versions(p1, p2)

        self.assertEqual(diff["policy_id"], "test_finance")
        self.assertEqual(diff["from_version"], "1.0.0")
        self.assertEqual(diff["to_version"], "1.1.0")

        # Allowed tools additions and deletions
        self.assertEqual(diff["added_allowed_tools"], ["write_file"])
        self.assertEqual(diff["removed_allowed_tools"], ["read_file"])

        # Forbidden tools additions and deletions
        self.assertEqual(diff["added_forbidden_tools"], ["delete_file"])
        self.assertEqual(diff["removed_forbidden_tools"], [])

        # Changed status and description
        self.assertEqual(diff["changed_status"], {"from": "active", "to": "inactive"})
        self.assertEqual(diff["changed_description"], {"from": "Finance version 1", "to": "Finance version 1.1 modified"})

        # Constraints
        constraints_diff = diff["changed_constraints"]
        self.assertEqual(constraints_diff["added"], {"new_constraint": True})
        self.assertEqual(constraints_diff["removed"], {})
        self.assertEqual(constraints_diff["modified"], {"max_amount": {"from": 1000, "to": 5000}})

    def test_timeline_chronological_ordering(self):
        # Insert events with structured timestamps and order
        events = [
            {"session_id": "sess_1", "action_hash": "hash_1", "tool_name": "t1", "event_type": "POLICY_LOADED", "timestamp": "2026-06-21T12:00:01Z"},
            {"session_id": "sess_1", "action_hash": "hash_1", "tool_name": "t1", "event_type": "PROOF_GENERATION_STARTED", "timestamp": "2026-06-21T12:00:02Z"},
            {"session_id": "sess_1", "action_hash": "hash_1", "tool_name": "t1", "event_type": "PROOF_GENERATION_COMPLETED", "timestamp": "2026-06-21T12:00:03Z"},
            {"session_id": "sess_1", "action_hash": "hash_1", "tool_name": "t1", "event_type": "PROOF_VERIFICATION_COMPLETED", "timestamp": "2026-06-21T12:00:04Z"},
        ]

        for ev in events:
            self.repo.insert_event(ev, recalculate_hashes=True)

        fetched = load_audit_logs()
        # Verify events are stored and retrieved in ascending order
        self.assertEqual(len(fetched), 4)
        self.assertEqual(fetched[0]["event_type"], "POLICY_LOADED")
        self.assertEqual(fetched[1]["event_type"], "PROOF_GENERATION_STARTED")
        self.assertEqual(fetched[2]["event_type"], "PROOF_GENERATION_COMPLETED")
        self.assertEqual(fetched[3]["event_type"], "PROOF_VERIFICATION_COMPLETED")

    def test_chain_verification_tamper_detection(self):
        # Insert sequential chained events
        self.repo.insert_event({"session_id": "sess_1", "tool_name": "t1", "status": "EXECUTED"}, recalculate_hashes=True)
        self.repo.insert_event({"session_id": "sess_2", "tool_name": "t2", "status": "EXECUTED"}, recalculate_hashes=True)

        # Check chain is valid initially
        metrics = get_dashboard_overview_metrics()
        self.assertEqual(metrics["chain_status"], "VALID")
        self.assertEqual(metrics["broken_links_count"], 0)

        # Tamper database manually
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE audit_events SET status = 'EXECUTED_TAMPERED' WHERE id = 1")
        row = cursor.execute("SELECT raw_data FROM audit_events WHERE id = 1").fetchone()
        event_dict = json.loads(row[0])
        event_dict["status"] = "EXECUTED_TAMPERED"
        cursor.execute("UPDATE audit_events SET raw_data = ? WHERE id = 1", (json.dumps(event_dict),))
        conn.commit()
        conn.close()

        # Check chain integrity detection after tampering
        get_dashboard_overview_metrics.clear()
        metrics_tampered = get_dashboard_overview_metrics()
        self.assertEqual(metrics_tampered["chain_status"], "INVALID")
        self.assertGreater(metrics_tampered["broken_links_count"], 0)

if __name__ == "__main__":
    unittest.main()
