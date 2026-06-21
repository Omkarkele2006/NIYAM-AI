import unittest
import os
import sys
import json
import uuid
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from schema.audit_repository import AuditRepository
from schema.policy import (
    Policy,
    PolicyRepository,
    PolicyValidationError,
    compare_versions,
    validate_policy_data
)
from schema.intent_contract import IntentContract
from schema.tool_gate import ToolAuthorityGate, GovernanceValidationError
from schema.interceptor import intercept_execution, InterceptionBlocked
from schema.governance_service import (
    load_governed_policy,
    seal_policy_contract,
    activate_policy_version,
    deactivate_policy_version
)


class TestPolicyGovernance(unittest.TestCase):
    def setUp(self):
        # We will use a unique test database for auditing during service/interceptor logs
        self.test_db = f"test_audit_policy_{uuid.uuid4().hex[:8]}.db"
        self.repo_instance = AuditRepository(REPO_ROOT / self.test_db)
        
        # Patch the default DB path class attribute for new connections
        self.db_path_patcher = patch("schema.audit_repository.DEFAULT_DB_PATH", REPO_ROOT / self.test_db)
        self.db_path_patcher.start()

        # Patch the active audit logger repo directly to catch module-level instances
        self.logger_patcher = patch("schema.audit_logger._repo", self.repo_instance)
        self.logger_patcher.start()

        # Set up a temp directory for policy files to keep repository clean
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo = PolicyRepository(directory=self.temp_dir.name)

        # Seed standard valid tools for testing
        self.valid_tools = {
            "proceed_transaction",
            "send_email",
            "read_file",
            "write_file",
            "delete_file",
            "execute_shell",
            "api_call",
            "database_query"
        }

    def tearDown(self):
        self.logger_patcher.stop()
        self.db_path_patcher.stop()
        db_path = REPO_ROOT / self.test_db
        if db_path.exists():
            try:
                db_path.unlink()
            except OSError:
                pass
        self.temp_dir.cleanup()

    # ==========================================
    # 1. FUNCTIONAL TESTS
    # ==========================================
    def test_load_default_policies(self):
        # Load live default policy files from the repository's policies directory
        repo_live = PolicyRepository()
        
        finance_p = repo_live.load_policy("finance_policy", "1.0.0")
        self.assertEqual(finance_p.policy_id, "finance_policy")
        self.assertEqual(finance_p.version, "1.0.0")
        self.assertIn("proceed_transaction", finance_p.allowed_tools)

        research_p = repo_live.load_policy("research_policy", "1.0.0")
        self.assertEqual(research_p.policy_id, "research_policy")
        self.assertEqual(research_p.version, "1.0.0")
        self.assertIn("read_file", research_p.allowed_tools)

    def test_policy_to_contract_conversion(self):
        policy_data = {
            "policy_id": "test_policy",
            "version": "1.2.0",
            "status": "draft",
            "created_at": "2026-06-21T12:00:00Z",
            "description": "Test policy description",
            "allowed_tools": ["read_file"],
            "forbidden_tools": ["delete_file"],
            "constraints": {},
            "metadata": {}
        }
        policy = self.repo.load_policy_from_dict(policy_data, valid_tools=self.valid_tools)
        contract = policy.to_contract(agent_name="AgentX", user_task="Read sensitive files")
        
        self.assertIsInstance(contract, IntentContract)
        self.assertEqual(contract.agent_name, "AgentX")
        self.assertEqual(contract.user_task, "Read sensitive files")
        self.assertEqual(contract.allowed_tools, ["read_file"])
        self.assertEqual(contract.forbidden_tools, ["delete_file"])
        self.assertEqual(contract.policy_id, "test_policy")
        self.assertEqual(contract.policy_version, "1.2.0")

    # ==========================================
    # 2. VALIDATION ENGINE TESTS
    # ==========================================
    def test_validation_missing_required_fields(self):
        invalid_data = {
            "policy_id": "finance_policy",
            "version": "1.0.0"
            # allowed_tools, forbidden_tools, description, status, created_at missing
        }
        errors = validate_policy_data(invalid_data, valid_tools=self.valid_tools)
        self.assertTrue(any("Missing required field" in e for e in errors))

    def test_validation_invalid_version_format(self):
        invalid_versions = ["v1.0", "1", "1.a", "1.0.0-alpha"]
        for ver in invalid_versions:
            data = {
                "policy_id": "test_p",
                "version": ver,
                "status": "draft",
                "created_at": "2026-06-21T12:00:00Z",
                "description": "Desc",
                "allowed_tools": ["read_file"],
                "forbidden_tools": []
            }
            errors = validate_policy_data(data, valid_tools=self.valid_tools)
            self.assertTrue(any("version format" in e.lower() for e in errors), f"Version '{ver}' should fail validation")

    def test_validation_duplicate_tools(self):
        data = {
            "policy_id": "test_p",
            "version": "1.0.0",
            "status": "draft",
            "created_at": "2026-06-21T12:00:00Z",
            "description": "Desc",
            "allowed_tools": ["read_file", "read_file"],
            "forbidden_tools": ["delete_file", "delete_file"]
        }
        errors = validate_policy_data(data, valid_tools=self.valid_tools)
        self.assertTrue(any("Duplicate tools in allowed_tools" in e for e in errors))
        self.assertTrue(any("Duplicate tools in forbidden_tools" in e for e in errors))

    def test_validation_conflicting_tools(self):
        data = {
            "policy_id": "test_p",
            "version": "1.0.0",
            "status": "draft",
            "created_at": "2026-06-21T12:00:00Z",
            "description": "Desc",
            "allowed_tools": ["read_file", "proceed_transaction"],
            "forbidden_tools": ["proceed_transaction", "delete_file"]
        }
        errors = validate_policy_data(data, valid_tools=self.valid_tools)
        self.assertTrue(any("Conflicting tools declared in both allowed and forbidden" in e for e in errors))

    def test_validation_invalid_tool_reference(self):
        data = {
            "policy_id": "test_p",
            "version": "1.0.0",
            "status": "draft",
            "created_at": "2026-06-21T12:00:00Z",
            "description": "Desc",
            "allowed_tools": ["send_carrier_pigeon"],
            "forbidden_tools": ["delete_file"]
        }
        errors = validate_policy_data(data, valid_tools=self.valid_tools)
        self.assertTrue(any("is not registered in the system" in e for e in errors))

    # ==========================================
    # 3. VERSIONING & IMMUTABILITY TESTS
    # ==========================================
    def test_policy_immutability(self):
        policy_data = {
            "policy_id": "imm_policy",
            "version": "1.0.0",
            "status": "draft",
            "created_at": "2026-06-21T12:00:00Z",
            "description": "Test policy",
            "allowed_tools": ["read_file"],
            "forbidden_tools": ["delete_file"]
        }
        policy = Policy(**policy_data)
        
        # Save version 1.0.0
        self.repo.save_policy(policy)
        
        # Saving again without overwrite should fail (immutability)
        with self.assertRaises(FileExistsError):
            self.repo.save_policy(policy, overwrite=False)
            
        # Overwrite=True should succeed
        dest = self.repo.save_policy(policy, overwrite=True)
        self.assertTrue(dest.exists())

    def test_retrieve_sorted_versions(self):
        base_data = {
            "policy_id": "multi_version",
            "status": "draft",
            "created_at": "2026-06-21T12:00:00Z",
            "description": "Desc",
            "allowed_tools": ["read_file"],
            "forbidden_tools": []
        }
        
        # Save unordered versions: 2.0.0, 1.0.0, 1.10.0
        self.repo.save_policy(Policy(version="2.0.0", **base_data))
        self.repo.save_policy(Policy(version="1.0.0", **base_data))
        self.repo.save_policy(Policy(version="1.10.0", **base_data))
        
        versions = self.repo.retrieve_versions("multi_version")
        version_strings = [p.version for p in versions]
        
        # Semantic sorting: 1.0.0 -> 1.10.0 -> 2.0.0
        self.assertEqual(version_strings, ["1.0.0", "1.10.0", "2.0.0"])

    # ==========================================
    # 4. DIFF ENGINE TESTS
    # ==========================================
    def test_policy_diff_engine(self):
        p1 = Policy(
            policy_id="diff_policy",
            version="1.0.0",
            status="draft",
            created_at="2026-06-21T12:00:00Z",
            description="First draft",
            allowed_tools=["read_file", "proceed_transaction"],
            forbidden_tools=["send_email"],
            constraints={"amount_limit": 100}
        )
        p2 = Policy(
            policy_id="diff_policy",
            version="1.1.0",
            status="active",
            created_at="2026-06-21T13:00:00Z",
            description="Second draft",
            allowed_tools=["read_file", "write_file"],
            forbidden_tools=["send_email", "delete_file"],
            constraints={"amount_limit": 200, "daily_cap": 1000}
        )
        
        diff = compare_versions(p1, p2)
        
        self.assertEqual(diff["policy_id"], "diff_policy")
        self.assertEqual(diff["from_version"], "1.0.0")
        self.assertEqual(diff["to_version"], "1.1.0")
        
        # Changes to allowed_tools
        self.assertEqual(diff["added_allowed_tools"], ["write_file"])
        self.assertEqual(diff["removed_allowed_tools"], ["proceed_transaction"])
        
        # Changes to forbidden_tools
        self.assertEqual(diff["added_forbidden_tools"], ["delete_file"])
        self.assertEqual(diff["removed_forbidden_tools"], [])
        
        # Changes to status/desc
        self.assertEqual(diff["changed_status"], {"from": "draft", "to": "active"})
        self.assertEqual(diff["changed_description"], {"from": "First draft", "to": "Second draft"})
        
        # Changes to constraints
        self.assertEqual(diff["changed_constraints"]["added"], {"daily_cap": 1000})
        self.assertEqual(diff["changed_constraints"]["modified"], {"amount_limit": {"from": 100, "to": 200}})

    # ==========================================
    # 5. AUDIT EVENT LOG INTEGRATION TESTS
    # ==========================================
    @patch("schema.governance_service.PolicyRepository")
    def test_audit_logs_for_policy_lifecycle(self, mock_repo_class):
        # Setup mock repository to avoid filesystem access
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        
        policy = Policy(
            policy_id="audit_policy",
            version="1.0.0",
            status="draft",
            created_at="2026-06-21T12:00:00Z",
            description="Test description",
            allowed_tools=["proceed_transaction"],
            forbidden_tools=["send_email"]
        )
        mock_repo.load_policy.return_value = policy
        mock_repo.retrieve_versions.return_value = [policy]

        # 1. Load Governed Policy (emits LOADED and VALIDATED)
        loaded = load_governed_policy("audit_policy", "1.0.0")
        
        # 2. Seal contract (emits POLICY_SEALED)
        contract = loaded.to_contract(agent_name="AgentA", user_task="Run task")
        seal_policy_contract(contract)
        
        # 3. Activate policy (emits POLICY_VERSION_ACTIVATED)
        activate_policy_version("audit_policy", "1.0.0")
        
        # 4. Deactivate policy (emits POLICY_VERSION_DEACTIVATED)
        deactivate_policy_version("audit_policy", "1.0.0")

        # Query all audit logs from test SQLite db
        logs = self.repo_instance.fetch_events()
        
        event_types = [log.get("event_type") for log in logs]
        
        self.assertIn("POLICY_LOADED", event_types)
        self.assertIn("POLICY_VALIDATED", event_types)
        self.assertIn("POLICY_SEALED", event_types)
        self.assertIn("POLICY_VERSION_ACTIVATED", event_types)
        self.assertIn("POLICY_VERSION_DEACTIVATED", event_types)

    # ==========================================
    # 6. EXPLAINABILITY & FAIL-CLOSED INTEGRATION TESTS
    # ==========================================
    def test_explainability_in_validation_errors(self):
        policy = Policy(
            policy_id="test_exp_policy",
            version="2.0.4",
            status="active",
            created_at="2026-06-21T12:00:00Z",
            description="Explainability test policy",
            allowed_tools=["proceed_transaction"],
            forbidden_tools=["send_email"]
        )
        
        # Create and seal contract
        contract = policy.to_contract(agent_name="AgentX", user_task="Execute payments")
        contract.seal()
        
        gate = ToolAuthorityGate(contract)
        
        # Forbidden tool trigger
        with self.assertRaises(GovernanceValidationError) as context:
            gate.validate_tool("send_email")
            
        err = context.exception
        self.assertEqual(err.policy, "test_exp_policy_v2.0.4")
        self.assertEqual(err.rule, "forbidden_tools")
        self.assertIn("forbidden by active policy 'test_exp_policy_v2.0.4'", err.reason)
        
        # Disallowed tool trigger
        with self.assertRaises(GovernanceValidationError) as context:
            gate.validate_tool("delete_file")
            
        err = context.exception
        self.assertEqual(err.policy, "test_exp_policy_v2.0.4")
        self.assertEqual(err.rule, "allowed_tools")
        self.assertIn("not allowed by active policy 'test_exp_policy_v2.0.4'", err.reason)

    @patch("schema.interceptor._env_report", {"valid": True, "errors": []})
    def test_interceptor_explainability_logging(self):
        policy = Policy(
            policy_id="log_exp_policy",
            version="1.5.0",
            status="active",
            created_at="2026-06-21T12:00:00Z",
            description="Interceptor logging explainability policy",
            allowed_tools=["proceed_transaction"],
            forbidden_tools=["send_email"]
        )
        contract = policy.to_contract(agent_name="AgentL", user_task="Process transactions")
        contract.seal()
        
        cfi = MagicMock()
        gate = ToolAuthorityGate(contract)
        
        # Execute blocked action through interceptor
        with self.assertRaises(InterceptionBlocked):
            intercept_execution(
                tool_name="send_email",
                payload={"to": "user@email.com", "data": "blocked payload"},
                contract=contract,
                cfi=cfi,
                gate=gate,
                execute_func=lambda t, p: "OK"
            )

        # Retrieve the generated audit event from test SQLite db
        logs = self.repo_instance.fetch_events(status="BLOCKED")
        
        # Find the latest blocked log event for this session
        relevant_logs = [log for log in logs if log.get("session_id") == contract.session_id]
        self.assertTrue(len(relevant_logs) > 0)
        
        blocked_log = relevant_logs[0]
        self.assertEqual(blocked_log.get("policy"), "log_exp_policy_v1.5.0")
        self.assertEqual(blocked_log.get("rule"), "forbidden_tools")
        self.assertIn("forbidden by active policy 'log_exp_policy_v1.5.0'", blocked_log.get("reason"))


if __name__ == '__main__':
    unittest.main()
