"""
Governed execution runtime for NIYAM-AI.

This module wraps the raw ``execute_func`` call (interceptor STEP 7) with:

  - Deterministic execution IDs bound to the verified proof
  - A finite state machine enforcing PENDING → RUNNING → terminal/TERMINATED
  - Timeout enforcement using ``GovernedToolMetadata.timeout_seconds``
  - Structured ``RuntimeGovernanceEvent`` records replacing print() leaks
  - Optional per-tool cleanup hooks with fail-safe isolation
  - A Process Isolation Layer containing SandboxExecutor implementations.

Integration point
-----------------
The runtime sits **between** interceptor STEP 6 (``verified == True``) and
STEP 7 (``execute_func(tool_name, payload)``). It does NOT replace the
interceptor — it is an execution envelope that strengthens STEP 7 only.

Security invariants
-------------------
  - ``GovernedExecutionContext`` cannot be instantiated with
    ``proof_verified != True`` (raises ``ValueError`` at ``__post_init__``).
  - The planner never receives a reference to this module.
  - ``InterceptionBlocked`` remains the sole blocking signal — this module
    re-raises ordinary ``Exception`` so the interceptor's existing broad
    ``except`` catches it unchanged.
  - Cleanup hook failures are isolated and never mask execution failures.
"""

from __future__ import annotations

import hashlib
import json
import time
import multiprocessing
import pickle
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_TIMEOUT_SECONDS: int = 10
"""Fallback timeout when no tool metadata is available."""


# ---------------------------------------------------------------------------
# ExecutionState — finite state machine for one execution attempt
# ---------------------------------------------------------------------------

class ExecutionState(Enum):
    """Lifecycle states for a single governed tool execution."""

    PENDING    = "PENDING"
    RUNNING    = "RUNNING"
    COMPLETED  = "COMPLETED"
    TIMED_OUT  = "TIMED_OUT"
    FAILED     = "FAILED"
    TERMINATED = "TERMINATED"
    CLEANED_UP = "CLEANED_UP"


# Allowed (source → target) transitions. All others raise ValueError.
_VALID_TRANSITIONS: frozenset[tuple[ExecutionState, ExecutionState]] = frozenset({
    (ExecutionState.PENDING,    ExecutionState.RUNNING),
    (ExecutionState.RUNNING,    ExecutionState.COMPLETED),
    (ExecutionState.RUNNING,    ExecutionState.TIMED_OUT),
    (ExecutionState.RUNNING,    ExecutionState.FAILED),
    (ExecutionState.RUNNING,    ExecutionState.TERMINATED),
    (ExecutionState.TIMED_OUT,  ExecutionState.CLEANED_UP),
    (ExecutionState.FAILED,     ExecutionState.CLEANED_UP),
    (ExecutionState.TERMINATED, ExecutionState.CLEANED_UP),
})


# ---------------------------------------------------------------------------
# Deterministic execution ID derivation
# ---------------------------------------------------------------------------

def derive_execution_id(
    *,
    action_hash: str,
    intent_hash: str,
    proof_path: str,
    timestamp_ns: int | None = None,
) -> str:
    """Return a SHA-256 execution ID unique to this exact invocation.

    The ID binds the verified proof path and nanosecond-precision timestamp
    to the action, making replayed executions forensically distinguishable.
    """

    if timestamp_ns is None:
        timestamp_ns = time.time_ns()

    normalized = json.dumps(
        {
            "action_hash": action_hash,
            "intent_hash": intent_hash,
            "proof_path": proof_path,
            "timestamp_ns": timestamp_ns,
        },
        sort_keys=True,
    )
    return hashlib.sha256(normalized.encode()).hexdigest()


# ---------------------------------------------------------------------------
# GovernedExecutionContext — frozen proof-bound execution identity
# ---------------------------------------------------------------------------

def _utc_now_iso() -> str:
    """Return UTC now as ISO-8601."""
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class GovernedExecutionContext:
    """Immutable identity of one governed tool execution attempt.

    **Hard-fail invariant:** instantiating with ``proof_verified != True``
    raises ``ValueError`` at ``__post_init__``. This makes it architecturally
    impossible to create an execution context without a verified proof.
    """

    execution_id: str
    tool_name: str
    action_hash: str
    intent_hash: str
    proof_path: str
    proof_verified: bool
    session_id: str
    started_at: str = field(default_factory=_utc_now_iso)
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS
    tool_metadata_hash: str | None = None

    def __post_init__(self) -> None:
        if self.proof_verified is not True:
            raise ValueError(
                "GovernedExecutionContext requires proof_verified=True. "
                "Execution context cannot exist without a verified proof."
            )

        if not self.execution_id:
            raise ValueError("execution_id is required.")

        if not self.tool_name or not self.tool_name.strip():
            raise ValueError("tool_name is required.")

    def to_dict(self) -> dict[str, Any]:
        """Return a log-safe dictionary (no callables, no references)."""

        return {
            "execution_id": self.execution_id,
            "tool_name": self.tool_name,
            "action_hash": self.action_hash,
            "intent_hash": self.intent_hash,
            "proof_path": self.proof_path,
            "proof_verified": self.proof_verified,
            "session_id": self.session_id,
            "started_at": self.started_at,
            "timeout_seconds": self.timeout_seconds,
            "tool_metadata_hash": self.tool_metadata_hash,
        }


# ---------------------------------------------------------------------------
# RuntimeGovernanceEvent — structured replacement for print() statements
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RuntimeGovernanceEvent:
    """A structured governance event emitted by the execution runtime.

    These events replace the unstructured print() calls in the interceptor
    and provide forensic-grade execution telemetry.
    """

    event_type: str
    execution_id: str
    tool_name: str
    state: ExecutionState
    timestamp: str = field(default_factory=_utc_now_iso)
    session_id: str = ""
    detail: str | None = None
    duration_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable event record."""

        return {
            "event_type": self.event_type,
            "execution_id": self.execution_id,
            "tool_name": self.tool_name,
            "state": self.state.value,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "detail": self.detail,
            "duration_ms": self.duration_ms,
        }


# ---------------------------------------------------------------------------
# GovernedExecutionResult — outcome of one runtime-managed execution
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GovernedExecutionResult:
    """Structured result returned by ``GovernedExecutionRuntime.execute_governed``."""

    execution_id: str
    tool_name: str
    state: ExecutionState
    result: Any = None
    error: str | None = None
    duration_ms: float = 0.0
    events: tuple[RuntimeGovernanceEvent, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable result record."""

        return {
            "execution_id": self.execution_id,
            "tool_name": self.tool_name,
            "state": self.state.value,
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "events": [e.to_dict() for e in self.events],
        }


# ---------------------------------------------------------------------------
# Process Isolation Layer - Sandbox Executors
# ---------------------------------------------------------------------------

class BaseSandboxExecutor:
    """
    Abstract interface defining execution containment strategies for registered tools.
    """
    def execute(self, tool_name: str, payload: dict[str, Any], timeout: int) -> Any:
        raise NotImplementedError()


def _subprocess_worker(pipe: multiprocessing.connection.Connection, execute_func: Callable[[str, dict[str, Any]], Any], tool_name: str, payload: dict[str, Any]):
    """Target function spawned inside the subprocess containing execute_func execution."""
    try:
        res = execute_func(tool_name, payload)
        pipe.send((True, res))
    except Exception as exc:
        pipe.send((False, str(exc)))
    finally:
        pipe.close()


class SubprocessSandboxExecutor(BaseSandboxExecutor):
    """
    Process Isolation Layer Strategy:
    Runs tool callables inside a separate OS process for memory isolation and containment.

    Why subprocess execution is preferred over thread execution:
    1. Memory Separation: Subprocess executes in a separate OS memory space, preventing
       tool code from directly reading or writing parent interpreter state or accessing sealed intent contracts.
    2. Termination Support: Spawning a separate process allows clean, forceful termination (via .terminate()
       and .kill()) when timeouts are exceeded. In contrast, Python threads cannot be forcefully killed
       from the parent thread, which leads to active zombie threads leaking resources in background loops.
    """
    def __init__(self, execute_func: Callable[[str, dict[str, Any]], Any]):
        self.execute_func = execute_func

    def execute(self, tool_name: str, payload: dict[str, Any], timeout: int) -> Any:
        parent_conn, child_conn = multiprocessing.Pipe()
        
        process = multiprocessing.Process(
            target=_subprocess_worker,
            args=(child_conn, self.execute_func, tool_name, payload)
        )
        process.start()
        
        try:
            if parent_conn.poll(timeout):
                success, output = parent_conn.recv()
                if success:
                    return output
                else:
                    raise Exception(output)
            else:
                # Forcefully terminate to prevent zombie execution loops
                process.terminate()
                process.join(timeout=1.0)
                if process.is_alive():
                    process.kill()
                raise TimeoutError(f"Subprocess tool execution timed out after {timeout} seconds")
        finally:
            parent_conn.close()
            try:
                child_conn.close()
            except Exception:
                pass
            if process.is_alive():
                process.terminate()
                process.join()
            process.close()


class ThreadSandboxExecutor(BaseSandboxExecutor):
    """
    Fallback Execution Layer Strategy:
    Runs tool execution in a single thread inside the parent process memory boundary.

    WARNING:
    This serves purely as a fallback mechanism when multiprocessing/pickling is impossible
    (e.g., executing dynamically generated local mocks, non-picklable functions, or lambda callables).
    It does NOT provide process isolation or termination capability.
    """
    def __init__(self, execute_func: Callable[[str, dict[str, Any]], Any]):
        self.execute_func = execute_func

    def execute(self, tool_name: str, payload: dict[str, Any], timeout: int) -> Any:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.execute_func, tool_name, payload)
            try:
                return future.result(timeout=timeout)
            except FuturesTimeoutError:
                raise TimeoutError(f"Thread tool execution timed out after {timeout} seconds")


class SandboxExecutor(BaseSandboxExecutor):
    """
    Unified Sandbox Executor coordinating isolated subprocess runs
    with thread fallbacks in case of pickling constraints.
    """
    def __init__(self, execute_func: Callable[[str, dict[str, Any]], Any]):
        self.execute_func = execute_func
        self.subprocess_executor = SubprocessSandboxExecutor(execute_func)
        self.thread_executor = ThreadSandboxExecutor(execute_func)

    def execute(self, tool_name: str, payload: dict[str, Any], timeout: int) -> Any:
        try:
            # Try isolated execution first
            return self.subprocess_executor.execute(tool_name, payload, timeout)
        except (AttributeError, TypeError, pickle.PicklingError) as e:
            # Fallback when serialization is impossible (e.g. dynamic mock lambdas)
            print(f"[SandboxExecutor] Process isolation failed due to pickling constraints: {e}. Falling back to Thread sandbox.")
            return self.thread_executor.execute(tool_name, payload, timeout)


# ---------------------------------------------------------------------------
# GovernedExecutionRuntime
# ---------------------------------------------------------------------------

class GovernedExecutionRuntime:
    """Timeout-enforcing, state-tracked execution envelope.

    The runtime is **stateless between calls** — each ``execute_governed``
    invocation creates a fresh state machine. No shared mutable state exists
    between executions.

    Parameters
    ----------
    emit : callable, optional
        Receives each ``RuntimeGovernanceEvent``. Defaults to a no-op.
        Plug in a function that forwards events to the audit logger or an
        observability backend.
    cleanup_hooks : dict, optional
        Mapping of ``tool_name → callable(payload, context)``. Called only
        on TIMED_OUT, TERMINATED, or FAILED states. Hook failures are isolated.
    """

    def __init__(
        self,
        *,
        emit: Callable[[RuntimeGovernanceEvent], None] | None = None,
        cleanup_hooks: dict[str, Callable[..., None]] | None = None,
    ) -> None:
        self._emit = emit or (lambda _event: None)
        self._cleanup_hooks: dict[str, Callable[..., None]] = dict(cleanup_hooks or {})

    # -- public API --------------------------------------------------------

    def execute_governed(
        self,
        *,
        context: GovernedExecutionContext,
        execute_func: Callable[[str, dict[str, Any]], Any],
        payload: dict[str, Any],
    ) -> GovernedExecutionResult:
        """Run *execute_func* inside a governed execution envelope.

        This method is called from the interceptor at STEP 7. It:

        1. Validates that ``context.proof_verified is True`` (redundant with
           ``__post_init__`` but defence-in-depth).
        2. Transitions state PENDING → RUNNING, emits EXECUTION_STARTED.
        3. Invokes tool inside SandboxExecutor (Process sandbox or fallback).
        4. On success → COMPLETED + EXECUTION_COMPLETED event.
        5. On timeout → TERMINATED + EXECUTION_TERMINATED event + cleanup.
        6. On exception → FAILED + EXECUTION_FAILED event + cleanup.
        7. Returns ``GovernedExecutionResult`` with full event trace.

        On failure paths (5, 6), raises ``Exception`` so the interceptor's
        existing broad ``except`` catches it and raises ``InterceptionBlocked``.
        """

        # Defence-in-depth — context __post_init__ already enforces this.
        if context.proof_verified is not True:
            raise ValueError("Refusing execution: proof_verified is not True.")

        events: list[RuntimeGovernanceEvent] = []
        state = ExecutionState.PENDING

        def _emit_and_record(
            event_type: str,
            new_state: ExecutionState,
            detail: str | None = None,
            duration_ms: float | None = None,
        ) -> None:
            nonlocal state
            state = _transition(state, new_state)

            event = RuntimeGovernanceEvent(
                event_type=event_type,
                execution_id=context.execution_id,
                tool_name=context.tool_name,
                state=state,
                session_id=context.session_id,
                detail=detail,
                duration_ms=duration_ms,
            )
            events.append(event)
            self._emit(event)

        # -- PENDING → RUNNING -------------------------------------------
        _emit_and_record("EXECUTION_STARTED", ExecutionState.RUNNING)
        start_ns = time.monotonic_ns()

        try:
            # Instantiate Sandbox Executor for isolated runtime containment
            executor = SandboxExecutor(execute_func)
            result = executor.execute(context.tool_name, payload, context.timeout_seconds)

            elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000

            # -- RUNNING → COMPLETED -------------------------------------
            _emit_and_record(
                "EXECUTION_COMPLETED",
                ExecutionState.COMPLETED,
                duration_ms=elapsed_ms,
            )

            return GovernedExecutionResult(
                execution_id=context.execution_id,
                tool_name=context.tool_name,
                state=ExecutionState.COMPLETED,
                result=result,
                duration_ms=elapsed_ms,
                events=tuple(events),
            )

        except TimeoutError as exc:
            elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000

            # -- RUNNING → TERMINATED (to prevent zombies on timeout) ----
            _emit_and_record(
                "EXECUTION_TERMINATED",
                ExecutionState.TERMINATED,
                detail=str(exc),
                duration_ms=elapsed_ms,
            )

            self._run_cleanup(context, payload, events)

            raise Exception(
                f"Governed execution timed out after {context.timeout_seconds}s "
                f"[execution_id={context.execution_id[:16]}]: {exc}"
            )

        except Exception as exc:
            elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000

            # -- RUNNING → FAILED ----------------------------------------
            _emit_and_record(
                "EXECUTION_FAILED",
                ExecutionState.FAILED,
                detail=str(exc),
                duration_ms=elapsed_ms,
            )

            self._run_cleanup(context, payload, events)

            raise Exception(
                f"Governed execution failed: {exc} "
                f"[execution_id={context.execution_id[:16]}]"
            ) from exc

    # -- cleanup -----------------------------------------------------------

    def _run_cleanup(
        self,
        context: GovernedExecutionContext,
        payload: dict[str, Any],
        events: list[RuntimeGovernanceEvent],
    ) -> None:
        """Run the cleanup hook for a tool, if registered. Failures are isolated."""

        hook = self._cleanup_hooks.get(context.tool_name)
        if hook is None:
            return

        try:
            hook(payload, context)

            cleanup_event = RuntimeGovernanceEvent(
                event_type="CLEANUP_COMPLETED",
                execution_id=context.execution_id,
                tool_name=context.tool_name,
                state=ExecutionState.CLEANED_UP,
                session_id=context.session_id,
            )
            events.append(cleanup_event)
            self._emit(cleanup_event)

        except Exception as cleanup_exc:
            # Cleanup failure is logged but NEVER masks the execution failure.
            cleanup_fail_event = RuntimeGovernanceEvent(
                event_type="CLEANUP_FAILED",
                execution_id=context.execution_id,
                tool_name=context.tool_name,
                state=events[-1].state, # stay in TIMED_OUT/TERMINATED or FAILED
                session_id=context.session_id,
                detail=f"Cleanup hook failed: {cleanup_exc}",
            )
            events.append(cleanup_fail_event)
            self._emit(cleanup_fail_event)


# ---------------------------------------------------------------------------
# State transition enforcer
# ---------------------------------------------------------------------------

def _transition(current: ExecutionState, target: ExecutionState) -> ExecutionState:
    """Validate and execute a state transition.

    Raises ``ValueError`` on illegal transitions, making the state machine
    formally verifiable.
    """

    if (current, target) not in _VALID_TRANSITIONS:
        raise ValueError(
            f"Illegal execution state transition: {current.value} → {target.value}"
        )

    return target
