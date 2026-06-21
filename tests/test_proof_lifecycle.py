import unittest
import os
import sys
import json
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from schema.proof_lifecycle import (
    validate_proof_environment,
    validate_proof_artifacts,
    ProofState
)
from schema.zk_prover import generate_proof
from schema.verifier import verify_proof
from schema.interceptor import intercept_execution, InterceptionBlocked
from schema.intent_contract import IntentContract
from schema.control_flow import ControlFlowIntegrity
from schema.tool_gate import ToolAuthorityGate

# Regression check functions
from test_sandbox import test_sandbox_suite

class TestProofLifecycle(unittest.TestCase):
    def setUp(self):
        # We will use a unique test database for auditing during intercept checks
        self.test_db = f"test_audit_proof_{uuid.uuid4().hex[:8]}.db"
        self.patcher = patch("schema.audit_repository.DEFAULT_DB_PATH", REPO_ROOT / self.test_db)
        self.patcher.start()
        
        # Create a mock witness.json in the repo root for tests that validate structure
        self.witness_path = REPO_ROOT / "witness.json"
        self.had_witness = self.witness_path.exists()
        if not self.had_witness:
            with open(self.witness_path, "w", encoding="utf-8") as f:
                json.dump({"inputs": [["1"]], "outputs": [["1"]]}, f)
        
    def tearDown(self):
        self.patcher.stop()
        db_path = REPO_ROOT / self.test_db
        if db_path.exists():
            try:
                db_path.unlink()
            except OSError:
                pass
                
        # Clean up mock witness.json if we created it
        if not self.had_witness and self.witness_path.exists():
            try:
                self.witness_path.unlink()
            except OSError:
                pass

    # ==========================================
    # SUCCESS CASES
    # ==========================================
    @patch("schema.zk_prover.subprocess.run")
    @patch("schema.verifier.subprocess.run")
    @patch("schema.interceptor._env_report", {"valid": True, "errors": []})
    def test_zk_proof_lifecycle_success_path(self, mock_ver_run, mock_prov_run):
        # Setup mock subprocess returns to simulate ezkl binary success
        mock_prov_run.return_value.returncode = 0
        mock_ver_run.return_value.returncode = 0
        
        # Feature vector represents a safe execution payload
        features = [0.1, 0.2, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0]
        
        # Test proof generation
        proof_path = generate_proof(features)
        self.assertIsNotNone(proof_path)
        self.assertEqual(proof_path, "proof.json")
        
        # Test artifact structural check
        self.assertTrue(validate_proof_artifacts(proof_path, "witness.json"))
        
        # Test verification success
        verified = verify_proof(proof_path)
        self.assertTrue(verified)

    # ==========================================
    # FAILURE CASES
    # ==========================================
    @patch("schema.proof_lifecycle.check_ezkl_binary", return_value=False)
    def test_missing_ezkl_installation(self, mock_check):
        report = validate_proof_environment()
        self.assertFalse(report["valid"])
        self.assertFalse(report["ezkl_available"])
        self.assertTrue(any("EZKL utility is not available" in e for e in report["errors"]))

    def test_missing_required_artifact(self):
        # Test missing proving key
        with patch("schema.proof_lifecycle.REQUIRED_FILES", ["nonexistent_file.key"]):
            report = validate_proof_environment()
            self.assertFalse(report["valid"])
            self.assertTrue(any("nonexistent_file.key" in f for f in report["missing_files"]))

    @patch("schema.verifier.validate_proof_artifacts", return_value=False)
    def test_malformed_proof_rejected(self, mock_validate):
        # Verifier should fail-closed if artifacts are malformed
        verified = verify_proof("proof.json")
        self.assertFalse(verified)

    @patch("schema.verifier.VK_PATH", "nonexistent_vk.key")
    def test_missing_verification_key(self):
        verified = verify_proof("proof.json")
        self.assertFalse(verified)

    @patch("schema.verifier.TRUSTED_VK_HASH", "wrong_hash_value")
    def test_tampered_verification_key(self):
        verified = verify_proof("proof.json")
        self.assertFalse(verified)

    # ==========================================
    # SECURITY FAIL-CLOSED ENFORCEMENT
    # ==========================================
    @patch("schema.interceptor._env_report", {"valid": True, "errors": []})
    def test_interceptor_blocked_when_proof_generation_fails(self):
        contract = IntentContract(
            agent_name="TestAgent",
            user_task="Test",
            allowed_tools=["proceed_transaction"],
            forbidden_tools=[]
        )
        contract.seal()
        cfi = ControlFlowIntegrity(["proceed_transaction"])
        gate = ToolAuthorityGate(contract)
        
        def dummy_execute(tool_name, payload):
            return "SUCCESS"
            
        with patch("schema.interceptor.generate_proof", return_value=None):
            with self.assertRaises(InterceptionBlocked) as context:
                intercept_execution(
                    tool_name="proceed_transaction",
                    payload={"amount": 100, "recipient": "user1"},
                    contract=contract,
                    cfi=cfi,
                    gate=gate,
                    execute_func=dummy_execute
                )
            self.assertIn("Proof generation failed", str(context.exception))

    @patch("schema.interceptor._env_report", {"valid": True, "errors": []})
    def test_interceptor_blocked_when_proof_verification_fails(self):
        contract = IntentContract(
            agent_name="TestAgent",
            user_task="Test",
            allowed_tools=["proceed_transaction"],
            forbidden_tools=[]
        )
        contract.seal()
        cfi = ControlFlowIntegrity(["proceed_transaction"])
        gate = ToolAuthorityGate(contract)
        
        def dummy_execute(tool_name, payload):
            return "SUCCESS"

        with patch("schema.interceptor.generate_proof", return_value="proof.json"):
            with patch("schema.interceptor.verify_proof", return_value=False):
                with self.assertRaises(InterceptionBlocked) as context:
                    intercept_execution(
                        tool_name="proceed_transaction",
                        payload={"amount": 100, "recipient": "user1"},
                        contract=contract,
                        cfi=cfi,
                        gate=gate,
                        execute_func=dummy_execute
                    )
                self.assertIn("Proof verification failed", str(context.exception))

    def test_interceptor_blocked_when_env_invalid(self):
        contract = IntentContract(
            agent_name="TestAgent",
            user_task="Test",
            allowed_tools=["proceed_transaction"],
            forbidden_tools=[]
        )
        contract.seal()
        cfi = ControlFlowIntegrity(["proceed_transaction"])
        gate = ToolAuthorityGate(contract)
        
        # Force environment invalid
        with patch("schema.interceptor._env_report", {"valid": False, "errors": ["Mock environment missing"]}):
            with self.assertRaises(InterceptionBlocked) as context:
                intercept_execution(
                    tool_name="proceed_transaction",
                    payload={"amount": 100, "recipient": "user1"},
                    contract=contract,
                    cfi=cfi,
                    gate=gate,
                    execute_func=lambda t, p: "OK"
                )
            self.assertIn("EZKL environment is invalid", str(context.exception))

    # ==========================================
    # REGRESSION CASES
    # ==========================================
    def test_regressions_execution_containment(self):
        print("\n[Regression Test] Running Sandbox Executor tests...")
        try:
            test_sandbox_suite()
        except SystemExit as exc:
            self.assertEqual(exc.code, 0, "Sandbox execution tests failed")

if __name__ == '__main__':
    unittest.main()
