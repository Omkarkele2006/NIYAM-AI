import unittest
import os
import sys
import uuid
from pathlib import Path

# Ensure project root is in sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from schema.audit_repository import AuditRepository
from schema.governance_service import (
    get_latest_verified_execution,
    get_execution_forensics,
    get_proof_telemetry,
    get_decision_timeline,
    load_audit_logs,
    get_system_metrics,
    get_zkml_metrics,
    get_dashboard_overview_metrics
)

class TestDashboardTelemetry(unittest.TestCase):
    def setUp(self):
        # Clear Streamlit caches to prevent cross-test pollution
        load_audit_logs.clear()
        get_system_metrics.clear()
        get_zkml_metrics.clear()
        get_dashboard_overview_metrics.clear()

        # Unique test database for each test run to isolate test side-effects
        self.test_db = f"test_telemetry_{uuid.uuid4().hex[:8]}.db"
        self.db_path = REPO_ROOT / self.test_db
        
        # Patch AuditRepository.__init__ to redirect all DB connections to test_db
        self.original_audit_init = AuditRepository.__init__
        test_db_path = self.db_path
        
        def patched_audit_init(audit_self, db_path=None):
            audit_self.db_path = str(test_db_path)
            audit_self._init_db()
            
        AuditRepository.__init__ = patched_audit_init
        self.repo = AuditRepository()

    def tearDown(self):
        # Clear caches again
        load_audit_logs.clear()
        get_system_metrics.clear()
        get_zkml_metrics.clear()
        get_dashboard_overview_metrics.clear()

        # Restore original init methods
        AuditRepository.__init__ = self.original_audit_init
        
        if self.db_path.exists():
            try:
                self.db_path.unlink()
            except OSError:
                pass

    def test_get_latest_verified_execution_empty(self):
        # Ensure it returns None when no verified executions exist
        latest = get_latest_verified_execution()
        self.assertIsNone(latest)

    def test_get_latest_verified_execution_success(self):
        # Insert a non-verified execution
        self.repo.insert_event({
            "session_id": "sess_1",
            "execution_id": "exec_1",
            "tool_name": "proceed_transaction",
            "verification": False
        }, recalculate_hashes=True)
        
        # Insert a verified execution
        self.repo.insert_event({
            "session_id": "sess_2",
            "execution_id": "exec_2",
            "tool_name": "proceed_transaction",
            "verification": True,
            "proof_hash": "proof_hash_val",
            "witness_hash": "witness_hash_val",
            "input_hash": "input_hash_val"
        }, recalculate_hashes=True)
        
        latest = get_latest_verified_execution()
        self.assertIsNotNone(latest)
        self.assertEqual(latest["execution_id"], "exec_2")
        self.assertEqual(latest["proof_hash"], "proof_hash_val")

    def test_get_execution_forensics_missing(self):
        # Ensure it returns None for unknown execution ID
        forensics = get_execution_forensics("non_existent_id")
        self.assertIsNone(forensics)

    def test_get_execution_forensics_merging(self):
        # Insert multiple event stages for the same execution_id
        self.repo.insert_event({
            "session_id": "sess_1",
            "execution_id": "exec_1",
            "event_type": "PROOF_GENERATION_STARTED",
            "tool_name": "proceed_transaction",
            "witness_generation_ms": 12.5
        }, recalculate_hashes=True)
        
        self.repo.insert_event({
            "session_id": "sess_1",
            "execution_id": "exec_1",
            "event_type": "PROOF_GENERATION_COMPLETED",
            "tool_name": "proceed_transaction",
            "proof_generation_ms": 145.2,
            "proof_hash": "hash_proof"
        }, recalculate_hashes=True)
        
        self.repo.insert_event({
            "session_id": "sess_1",
            "execution_id": "exec_1",
            "event_type": "PROOF_VERIFICATION_COMPLETED",
            "tool_name": "proceed_transaction",
            "verification_ms": 32.1,
            "verification": True
        }, recalculate_hashes=True)
        
        forensics = get_execution_forensics("exec_1")
        self.assertIsNotNone(forensics)
        self.assertEqual(forensics["execution_id"], "exec_1")
        self.assertEqual(forensics["session_id"], "sess_1")
        self.assertEqual(forensics["proof_hash"], "hash_proof")
        self.assertEqual(forensics["witness_generation_ms"], 12.5)
        self.assertEqual(forensics["proof_generation_ms"], 145.2)
        self.assertEqual(forensics["verification_ms"], 32.1)
        self.assertEqual(forensics["audit_chain_status"], "VALID")

    def test_get_proof_telemetry(self):
        # Insert events with proving durations
        self.repo.insert_event({
            "session_id": "sess_1",
            "execution_id": "exec_1",
            "event_type": "PROOF_GENERATION_COMPLETED",
            "tool_name": "proceed_transaction",
            "witness_generation_ms": 10.0,
            "proof_generation_ms": 100.0,
            "verification_ms": 50.0,
            "total_proof_pipeline_ms": 160.0
        }, recalculate_hashes=True)
        
        self.repo.insert_event({
            "session_id": "sess_2",
            "execution_id": "exec_2",
            "event_type": "PROOF_GENERATION_COMPLETED",
            "tool_name": "proceed_transaction",
            "witness_generation_ms": 20.0,
            "proof_generation_ms": 200.0,
            "verification_ms": 100.0,
            "total_proof_pipeline_ms": 320.0
        }, recalculate_hashes=True)
        
        telemetry = get_proof_telemetry()
        self.assertIsNotNone(telemetry)
        
        metrics = telemetry["metrics"]
        self.assertEqual(metrics["witness_generation"]["avg"], 15.0)
        self.assertEqual(metrics["proof_generation"]["avg"], 150.0)
        self.assertEqual(metrics["verification"]["avg"], 75.0)
        self.assertEqual(metrics["total_pipeline"]["avg"], 240.0)
        
        # Verify recent runs ordering
        runs = telemetry["recent_runs"]
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[0]["execution_id"], "exec_2")  # Reverse ordered by ID
        self.assertEqual(runs[1]["execution_id"], "exec_1")

    def test_get_decision_timeline(self):
        # Insert sequential events for a session
        self.repo.insert_event({
            "session_id": "sess_1",
            "execution_id": "exec_1",
            "event_type": "POLICY_LOADED",
            "detail": "Loaded finance policy"
        }, recalculate_hashes=True)
        
        self.repo.insert_event({
            "session_id": "sess_1",
            "execution_id": "exec_1",
            "event_type": "POLICY_VALIDATED",
            "detail": "Validated schema"
        }, recalculate_hashes=True)
        
        self.repo.insert_event({
            "session_id": "sess_1",
            "execution_id": "exec_1",
            "event_type": "PROOF_GENERATION_COMPLETED",
            "detail": "Proof generated"
        }, recalculate_hashes=True)
        
        # Query timeline by execution ID
        timeline = get_decision_timeline("exec_1")
        self.assertEqual(len(timeline), 3)
        self.assertEqual(timeline[0]["event_type"], "POLICY_LOADED")
        self.assertEqual(timeline[1]["event_type"], "POLICY_VALIDATED")
        self.assertEqual(timeline[2]["event_type"], "PROOF_GENERATION_COMPLETED")

if __name__ == "__main__":
    unittest.main()
