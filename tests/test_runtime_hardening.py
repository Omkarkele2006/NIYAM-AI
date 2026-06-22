import unittest
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

from schema.zk_prover import generate_proof, get_execution_durations
from schema.verifier import verify_proof, sha256_file
from schema.interceptor import intercept_execution, InterceptionBlocked
from schema.audit_repository import AuditRepository
from schema.intent_contract import IntentContract
from schema.control_flow import ControlFlowIntegrity
from schema.tool_gate import ToolAuthorityGate

REPO_ROOT = Path(__file__).resolve().parents[1]

class TestRuntimeHardening(unittest.TestCase):
    def setUp(self):
        self.temp_dirs = []

    def tearDown(self):
        for d in self.temp_dirs:
            if os.path.exists(d):
                shutil.rmtree(d, ignore_errors=True)

    # 1. test_artifact_isolation_creates_execution_dir
    @patch("schema.zk_prover.subprocess.run")
    def test_artifact_isolation_creates_execution_dir(self, mock_run):
        mock_run.return_value.returncode = 0
        execution_id = "test_exec_123"
        features = [0.1] * 8
        
        temp_dir = tempfile.mkdtemp()
        self.temp_dirs.append(temp_dir)
        
        with patch("schema.zk_prover.REPO_ROOT", Path(temp_dir)):
            proof_path = generate_proof(features, execution_id=execution_id)
            self.assertIsNotNone(proof_path)
            
            exec_dir = Path(temp_dir) / "artifacts" / "executions" / execution_id
            self.assertTrue(exec_dir.exists())
            self.assertTrue((exec_dir / "input.json").exists())

    # 2. test_artifact_isolation_no_collision
    @patch("schema.zk_prover.subprocess.run")
    def test_artifact_isolation_no_collision(self, mock_run):
        mock_run.return_value.returncode = 0
        features = [0.1] * 8
        
        temp_dir = tempfile.mkdtemp()
        self.temp_dirs.append(temp_dir)
        
        with patch("schema.zk_prover.REPO_ROOT", Path(temp_dir)):
            proof_path_1 = generate_proof(features, execution_id="exec_A")
            proof_path_2 = generate_proof(features, execution_id="exec_B")
            
            self.assertIsNotNone(proof_path_1)
            self.assertIsNotNone(proof_path_2)
            self.assertNotEqual(proof_path_1, proof_path_2)
            self.assertIn("exec_A", proof_path_1)
            self.assertIn("exec_B", proof_path_2)

    # 3. test_proof_hash_recorded
    def test_proof_hash_recorded(self):
        temp_dir = tempfile.mkdtemp()
        self.temp_dirs.append(temp_dir)
        mock_file = Path(temp_dir) / "test_proof.json"
        content = b"mock proof content"
        mock_file.write_bytes(content)
        
        # SHA-256 of b"mock proof content" is 2c67094ad809cfe48e648f73641ef2ba5c1c95425d17547bfd539c2efedef1cd
        expected_hash = "2c67094ad809cfe48e648f73641ef2ba5c1c95425d17547bfd539c2efedef1cd"
        computed_hash = sha256_file(str(mock_file))
        self.assertEqual(computed_hash, expected_hash)

    # 4. test_witness_hash_recorded
    @patch("schema.zk_prover.subprocess.run")
    def test_witness_hash_recorded(self, mock_run):
        mock_run.return_value.returncode = 0
        features = [0.1] * 8
        temp_dir = tempfile.mkdtemp()
        self.temp_dirs.append(temp_dir)
        
        with patch("schema.zk_prover.REPO_ROOT", Path(temp_dir)):
            exec_id = "exec_witness_test"
            exec_dir = Path(temp_dir) / "artifacts" / "executions" / exec_id
            exec_dir.mkdir(parents=True, exist_ok=True)
            witness_file = exec_dir / "witness.json"
            witness_file.write_bytes(b"dummy witness content")
            proof_file = exec_dir / "proof.json"
            proof_file.write_bytes(b"dummy proof content")
            
            proof_path = generate_proof(features, execution_id=exec_id)
            self.assertIsNotNone(proof_path)
            
            proof_dir = Path(proof_path).parent
            witness_path = str(proof_dir / "witness.json")
            witness_hash = sha256_file(witness_path)
            self.assertIsNotNone(witness_hash)
            self.assertEqual(witness_hash, sha256_file(str(witness_file)))

    # 5. test_timeout_witness_generation
    @patch("schema.zk_prover.subprocess.run")
    @patch("schema.zk_prover.log_event")
    def test_timeout_witness_generation(self, mock_log, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(["ezkl", "gen-witness"], 120)
        features = [0.1] * 8
        
        temp_dir = tempfile.mkdtemp()
        self.temp_dirs.append(temp_dir)
        
        with patch("schema.zk_prover.REPO_ROOT", Path(temp_dir)):
            proof_path = generate_proof(features, execution_id="timeout_witness_id")
            self.assertIsNone(proof_path)
            mock_log.assert_called()
            logged_event = mock_log.call_args[0][0]
            self.assertEqual(logged_event["event_type"], "WITNESS_GENERATION_TIMEOUT")
            self.assertEqual(logged_event["status"], "BLOCKED")

    # 6. test_timeout_proof_generation
    @patch("schema.zk_prover.subprocess.run")
    @patch("schema.zk_prover.log_event")
    def test_timeout_proof_generation(self, mock_log, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0),
            subprocess.TimeoutExpired(["ezkl", "prove"], 300)
        ]
        features = [0.1] * 8
        
        temp_dir = tempfile.mkdtemp()
        self.temp_dirs.append(temp_dir)
        
        with patch("schema.zk_prover.REPO_ROOT", Path(temp_dir)):
            exec_id = "timeout_proof_id"
            exec_dir = Path(temp_dir) / "artifacts" / "executions" / exec_id
            exec_dir.mkdir(parents=True, exist_ok=True)
            (exec_dir / "witness.json").write_bytes(b"dummy")
            
            proof_path = generate_proof(features, execution_id=exec_id)
            self.assertIsNone(proof_path)
            mock_log.assert_called()
            logged_event = mock_log.call_args[0][0]
            self.assertEqual(logged_event["event_type"], "PROOF_GENERATION_TIMEOUT")
            self.assertEqual(logged_event["status"], "BLOCKED")

    # 7. test_timeout_verification
    @patch("schema.verifier.subprocess.run")
    @patch("schema.verifier.validate_proof_artifacts", return_value=True)
    @patch("schema.verifier.sha256_file", return_value="f519d8bddcf2801c194fb65e7d1ef628497462443e0891081e52c47bd99956e1")
    def test_timeout_verification(self, mock_sha, mock_validate, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(["ezkl", "verify"], 60)
        verified = verify_proof("proof.json")
        self.assertFalse(verified)

    # 8. test_feature_dimension_mismatch_blocked
    @patch("schema.interceptor._env_report", {"valid": True, "errors": []})
    def test_feature_dimension_mismatch_blocked(self):
        contract = IntentContract(
            agent_name="TestAgent",
            user_task="Test",
            allowed_tools=["proceed_transaction"],
            forbidden_tools=[]
        )
        contract.seal()
        cfi = ControlFlowIntegrity(["proceed_transaction"])
        gate = ToolAuthorityGate(contract)
        
        wrong_features = [0.1] * 7
        
        with patch("schema.interceptor.extract_features", return_value=wrong_features):
            with self.assertRaises(InterceptionBlocked) as context:
                intercept_execution(
                    tool_name="proceed_transaction",
                    payload={"amount": 100, "recipient": "user1"},
                    contract=contract,
                    cfi=cfi,
                    gate=gate,
                    execute_func=lambda t, p: "SUCCESS"
                )
            self.assertIn("Feature dimension mismatch", str(context.exception))

    # 9. test_feature_dimension_correct_passes
    @patch("schema.interceptor._env_report", {"valid": True, "errors": []})
    @patch("schema.interceptor.generate_proof")
    @patch("schema.interceptor.verify_proof", return_value=True)
    def test_feature_dimension_correct_passes(self, mock_ver, mock_gen):
        temp_dir = tempfile.mkdtemp()
        self.temp_dirs.append(temp_dir)
        mock_proof = Path(temp_dir) / "proof.json"
        mock_proof.write_bytes(b"dummy")
        mock_gen.return_value = str(mock_proof)
        
        contract = IntentContract(
            agent_name="TestAgent",
            user_task="Test",
            allowed_tools=["proceed_transaction"],
            forbidden_tools=[]
        )
        contract.seal()
        cfi = ControlFlowIntegrity(["proceed_transaction"])
        gate = ToolAuthorityGate(contract)
        
        correct_features = [0.1] * 8
        
        with patch("schema.interceptor.extract_features", return_value=correct_features):
            result = intercept_execution(
                tool_name="proceed_transaction",
                payload={"amount": 100, "recipient": "user1"},
                contract=contract,
                cfi=cfi,
                gate=gate,
                execute_func=lambda t, p: "EXECUTED_OK"
            )
            self.assertEqual(result, "EXECUTED_OK")

    # 10. test_runtime_metrics_recorded_in_audit
    @patch("schema.interceptor._env_report", {"valid": True, "errors": []})
    @patch("schema.interceptor.generate_proof")
    @patch("schema.interceptor.verify_proof", return_value=True)
    @patch("schema.interceptor.log_event")
    def test_runtime_metrics_recorded_in_audit(self, mock_log, mock_ver, mock_gen):
        temp_dir = tempfile.mkdtemp()
        self.temp_dirs.append(temp_dir)
        mock_proof = Path(temp_dir) / "proof.json"
        mock_proof.write_bytes(b"dummy")
        mock_gen.return_value = str(mock_proof)
        
        with patch("schema.interceptor.get_execution_durations", return_value={"witness_generation_ms": 120.0, "proof_generation_ms": 80.0}):
            contract = IntentContract(
                agent_name="TestAgent",
                user_task="Test",
                allowed_tools=["proceed_transaction"],
                forbidden_tools=[]
            )
            contract.seal()
            cfi = ControlFlowIntegrity(["proceed_transaction"])
            gate = ToolAuthorityGate(contract)
            
            intercept_execution(
                tool_name="proceed_transaction",
                payload={"amount": 100, "recipient": "user1"},
                contract=contract,
                cfi=cfi,
                gate=gate,
                execute_func=lambda t, p: "EXECUTED_OK"
            )
            
            calls = mock_log.call_args_list
            executed_event = None
            for call in calls:
                ev = call[0][0]
                if ev.get("status") == "EXECUTED":
                    executed_event = ev
                    break
            
            self.assertIsNotNone(executed_event)
            self.assertEqual(executed_event["witness_generation_ms"], 120.0)
            self.assertEqual(executed_event["proof_generation_ms"], 80.0)
            self.assertIsNotNone(executed_event["verification_ms"])
            self.assertIsNotNone(executed_event["total_proof_pipeline_ms"])

    # 11. test_audit_proof_hash_column
    def test_audit_proof_hash_column(self):
        db_file = f"test_audit_hardening_{int(time.time())}.db"
        repo = AuditRepository(db_file)
        
        event_dict = {
            "session_id": "metrics_session",
            "status": "EXECUTED",
            "proof_hash": "proof_hash_123",
            "witness_hash": "witness_hash_456",
            "input_hash": "input_hash_789",
            "witness_generation_ms": 150.0,
            "proof_generation_ms": 250.0,
            "verification_ms": 50.0,
            "total_proof_pipeline_ms": 450.0
        }
        
        repo.insert_event(event_dict, recalculate_hashes=True)
        
        metrics = repo.get_proof_runtime_metrics()
        self.assertEqual(metrics["witness_generation"]["avg"], 150.0)
        self.assertEqual(metrics["proof_generation"]["avg"], 250.0)
        self.assertEqual(metrics["verification"]["avg"], 50.0)
        self.assertEqual(metrics["total_pipeline"]["avg"], 450.0)
        
        try:
            if os.path.exists(db_file):
                os.unlink(db_file)
        except OSError:
            pass

    # 12. test_stale_flat_artifacts_not_used
    @patch("schema.zk_prover.subprocess.run")
    def test_stale_flat_artifacts_not_used(self, mock_run):
        mock_run.return_value.returncode = 0
        features = [0.1] * 8
        
        temp_dir = tempfile.mkdtemp()
        self.temp_dirs.append(temp_dir)
        
        flat_proof = Path(temp_dir) / "proof.json"
        flat_proof.write_bytes(b"stale content")
        
        with patch("schema.zk_prover.REPO_ROOT", Path(temp_dir)):
            execution_id = "fresh_isolated_run"
            
            exec_dir = Path(temp_dir) / "artifacts" / "executions" / execution_id
            exec_dir.mkdir(parents=True, exist_ok=True)
            
            # Write valid JSON formats to mock files so validate_proof_artifacts passes
            fresh_proof = exec_dir / "proof.json"
            proof_data = {"instances": [1, 2], "proof": [3, 4]}
            fresh_proof.write_text(json.dumps(proof_data), encoding="utf-8")
            
            fresh_witness = exec_dir / "witness.json"
            witness_data = {"inputs": [1], "outputs": [2]}
            fresh_witness.write_text(json.dumps(witness_data), encoding="utf-8")
            
            proof_path = generate_proof(features, execution_id=execution_id)
            self.assertIsNotNone(proof_path)
            self.assertNotEqual(proof_path, str(flat_proof))
            self.assertEqual(proof_path, str(fresh_proof))
            
            from schema.proof_lifecycle import validate_proof_artifacts
            self.assertTrue(validate_proof_artifacts(proof_path, str(exec_dir / "witness.json")))

if __name__ == '__main__':
    unittest.main()
