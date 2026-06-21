import sys
import time
import json
from pathlib import Path

# Add project root to sys.path to ensure imports work from within subdirectories
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from schema.intent_contract import IntentContract
from schema.orchestration.execution_runtime import (
    GovernedExecutionRuntime,
    GovernedExecutionContext,
    derive_execution_id,
    ExecutionState,
    RuntimeGovernanceEvent
)


# ==========================================
# MODULE LEVEL PICKLEABLE FUNCTIONS FOR PROCESS TESTS
# ==========================================
def mock_successful_tool(tool_name: str, payload: dict) -> str:
    return f"COMPLETED_{tool_name}_{payload.get('value', 0)}"

def mock_sleeping_tool(tool_name: str, payload: dict) -> str:
    sleep_time = payload.get("sleep", 5)
    time.sleep(sleep_time)
    return "FINISHED_SLEEP"

def mock_error_tool(tool_name: str, payload: dict) -> str:
    raise ValueError("Explicit tool execution error simulated")


def test_sandbox_suite():
    print("========================================")
    print("RUNNING RUNTIME PROCESS ISOLATION TESTS")
    print("========================================\n")

    # Capture emitted events for test assertions
    emitted_events: list[RuntimeGovernanceEvent] = []
    
    def mock_emitter(event: RuntimeGovernanceEvent):
        emitted_events.append(event)
        print(f"  [FSM Event] State: {event.state.value:<10} | Type: {event.event_type:<20} | Detail: {event.detail}")

    # Set up runtime
    runtime = GovernedExecutionRuntime(emit=mock_emitter)

    # Set up base context
    context = GovernedExecutionContext(
        execution_id=derive_execution_id(
            action_hash="mock_action_hash",
            intent_hash="mock_intent_hash",
            proof_path="proof.json"
        ),
        tool_name="mock_tool",
        action_hash="mock_action_hash",
        intent_hash="mock_intent_hash",
        proof_path="proof.json",
        proof_verified=True,
        session_id="mock_session_123",
        timeout_seconds=2  # short timeout for test runs
    )

    tests_run = 0
    tests_passed = 0

    def assert_test(name: str, condition: bool):
        nonlocal tests_run, tests_passed
        tests_run += 1
        print(f"\n[TEST {tests_run:02d}] {name} ... ", end="")
        if condition:
            print("PASSED")
            tests_passed += 1
        else:
            print("FAILED")

    # ---------------------------------------------
    # TEST 1: Successful Subprocess Isolation Execution
    # ---------------------------------------------
    emitted_events.clear()
    print("Executing safe picklable tool in subprocess process isolation...")
    
    res = runtime.execute_governed(
        context=context,
        execute_func=mock_successful_tool,
        payload={"value": 42}
    )
    
    assert_test(
        "Subprocess execution output check",
        res.result == "COMPLETED_mock_tool_42"
    )
    
    # Assert FSM sequence: PENDING -> RUNNING -> COMPLETED
    states = [e.state for e in emitted_events]
    assert_test(
        "Subprocess FSM transitions check",
        states == [ExecutionState.RUNNING, ExecutionState.COMPLETED]
    )

    # ---------------------------------------------
    # TEST 2: Subprocess Timeout and Force Termination
    # ---------------------------------------------
    emitted_events.clear()
    print("\nExecuting slow tool to trigger Process Isolation timeout...")
    
    start_time = time.monotonic()
    timeout_triggered = False
    try:
        runtime.execute_governed(
            context=context,
            execute_func=mock_sleeping_tool,
            payload={"sleep": 10}  # sleep 10s, timeout is 2s
        )
    except Exception as e:
        timeout_triggered = True
        print(f"  Caught expected timeout exception: {e}")
        
    duration = time.monotonic() - start_time
    
    assert_test(
        "Subprocess execution correctly timeout blocked",
        timeout_triggered
    )
    
    # Duration should be close to 2s, not 10s (proving termination)
    assert_test(
        "Subprocess execution terminated cleanly within time boundary",
        duration < 4.0
    )
    
    # Assert FSM sequence: RUNNING -> TERMINATED
    states = [e.state for e in emitted_events]
    assert_test(
        "Timeout FSM transitions check (terminated state reached)",
        ExecutionState.TERMINATED in states
    )

    # ---------------------------------------------
    # TEST 3: Force Exception Handling
    # ---------------------------------------------
    emitted_events.clear()
    print("\nExecuting error-prone tool inside process containment...")
    
    error_triggered = False
    try:
        runtime.execute_governed(
            context=context,
            execute_func=mock_error_tool,
            payload={}
        )
    except Exception as e:
        error_triggered = True
        print(f"  Caught expected tool execution error: {e}")

    assert_test(
        "Exception containment check",
        error_triggered
    )
    
    # Assert FSM sequence: RUNNING -> FAILED
    states = [e.state for e in emitted_events]
    assert_test(
        "Failed FSM transitions check",
        ExecutionState.FAILED in states
    )

    # ---------------------------------------------
    # TEST 4: Thread Execution Fallback (Non-pickleable)
    # ---------------------------------------------
    emitted_events.clear()
    print("\nExecuting non-pickleable local lambda function (should fall back to thread)...")
    
    # Local lambda references cannot be pickled by multiprocessing
    local_lambda = lambda tool, payload: f"THREAD_OUTPUT_{payload.get('key')}"
    
    res_fallback = runtime.execute_governed(
        context=context,
        execute_func=local_lambda,
        payload={"key": "secret"}
    )
    
    assert_test(
        "Thread fallback execution output check",
        res_fallback.result == "THREAD_OUTPUT_secret"
    )
    
    # Check that events were still emitted correctly
    states = [e.state for e in emitted_events]
    assert_test(
        "Thread fallback FSM transitions check",
        states == [ExecutionState.RUNNING, ExecutionState.COMPLETED]
    )

    print("\n----------------------------------------")
    print(f"PROCESS ISOLATION TEST SUITE: {tests_passed}/{tests_run} PASSED")
    print("----------------------------------------")
    
    if tests_passed != tests_run:
        sys.exit(1)


if __name__ == '__main__':
    test_sandbox_suite()
