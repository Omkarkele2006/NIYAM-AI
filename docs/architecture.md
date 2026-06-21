# NIYAM-AI Platform Architecture Overview

NIYAM-AI is a secure, verifiable governance platform designed to intercept, analyze, prove, verify, and log autonomous AI tool actions. It prevents prompt injection attacks or code bugs from bypassing intent restrictions by applying defense-in-depth policy verification and zero-knowledge Machine Learning (zkML) proofs.

---

## Architecture Blueprint

The system governs executions through a sequence of sequential layers before the final action is allowed to proceed:

```text
Prompt
  -> Intent Contract (Checks capability boundaries, matches session)
  -> Control Flow Integrity (Asserts step order compliance)
  -> Tool Gate (Checks against allowed/forbidden lists)
  -> zkML Pipeline (Extracts features, runs inference, generates proof)
  -> Verifier (Checks VK SHA-256 and verifies ZK-SNARK proof)
  -> Execution Runtime (Handles thread isolation, timeout, and cleanup)
  -> Audit Logger (Logs event context to append-only hash chain)
```

---

## Core Components

### 1. Intent Contract
*   **File Location**: [intent_contract.py](file:///c:/IMP/VIT/SY/SEM_2/EDI/NiyamAI-Proj-Code-Original/schema/intent_contract.py)
*   **Description**: Defines what capabilities (allowed tools) and restrictions (forbidden tools) are bound to a specific agent execution session.
*   **Security Properties**:
    *   **Post-Seal Immutability**: Transitioning list structures to immutable tuples using an overridden `__setattr__` block once sealed. Any subsequent mutation attempt triggers a runtime crash.
    *   **IntentHash**: Generates a deterministic SHA-256 hash of the sorted policy list, serving as a unique ID representing the approved policy configuration.

### 2. Tool Gate
*   **File Location**: [tool_gate.py](file:///c:/IMP/VIT/SY/SEM_2/EDI/NiyamAI-Proj-Code-Original/schema/tool_gate.py)
*   **Description**: The Tool Gate enforces the system's boundary defense checks through two distinct verification sub-layers:
    *   **Authorization Layer**: Validates tool names against the active `IntentContract`. Checks that the tool is listed under `allowed_tools` and is absent from `forbidden_tools`.
    *   **Schema Validation Layer**: Validates inputs using strict `jsonschema` payload validations. If a parameter doesn't meet defined ranges, constraints, or types, or carries unexpected additional fields (`additionalProperties: False`), validation fails.
*   **Defense Posture**:
    *   **Default-Deny for Missing Schemas**: If a tool is called that does not have a corresponding schema definition mapped, it is blocked automatically.
    *   **Structured Errors**: Validation errors raise a `GovernanceValidationError` formatting detailed contexts (tool, status, and precise failure message) into standard JSON strings for parsing or logging.

### 3. Interceptor
*   **File Location**: [interceptor.py](file:///c:/IMP/VIT/SY/SEM_2/EDI/NiyamAI-Proj-Code-Original/schema/interceptor.py)
*   **Description**: The central policy enforcement point (PEP) that coordinates the execution check sequence.
*   **Responsibility**: Intercepts requested tool calls, coordinates CFI, Tool Gate authorization and schema checks, zkML feature extraction, proof generation, and verification before dispatching to the execution runtime. In case of verification failure, it flags security alerts and logs the blocked action.

### 4. zkML Pipeline
*   **Files**: 
    *   [feature_extractor.py](file:///c:/IMP/VIT/SY/SEM_2/EDI/NiyamAI-Proj-Code-Original/schema/ml/feature_extractor.py) (Extracts 8 normalized feature signals including length, risk indexes, keyword jailbreaks, and injection tokens).
    *   [zk_prover.py](file:///c:/IMP/VIT/SY/SEM_2/EDI/NiyamAI-Proj-Code-Original/schema/zk_prover.py) (Compiles feature values, calls EZKL for witness parsing, and generates SNARK proof files).
*   **Description**: Converts prompt parameters and metadata into deterministic float representations. It generates a cryptographic proof attesting to correct ML-inference validation without relying on unproven claims.

### 5. Verifier
*   **File Location**: [verifier.py](file:///c:/IMP/VIT/SY/SEM_2/EDI/NiyamAI-Proj-Code-Original/schema/verifier.py)
*   **Description**: Checks proof validity against the compiled verification key `vk.key`.
*   **Integrity Defense**: Before running EZKL verification, it checks the SHA-256 hash of `vk.key` against a trusted, hardcoded hash. This prevents attackers from bypassing ZK validation by swapping the verification key.

### 6. Execution Runtime
*   **File Location**: [execution_runtime.py](file:///c:/IMP/VIT/SY/SEM_2/EDI/NiyamAI-Proj-Code-Original/schema/orchestration/execution_runtime.py)
*   **Description**: The Isolated Execution Runtime managing the approved execution steps.
*   **Key Controls**:
    *   **FSM State Transitions**: Enforces logical lifecycle transitions (`PENDING` -> `RUNNING` -> `COMPLETED` / `FAILED` / `TERMINATED` -> `CLEANED_UP`).
    *   **Timeout Handling**: Runs executions inside the Process Isolation Layer (`SubprocessSandboxExecutor`), allowing clean process termination to prevent zombie execution loops.
    *   **Failsafe Cleanups**: Triggers custom, tool-specific rollback routines in case of timeouts, execution termination, or execution errors.

### 7. Audit Logger & SQLite Backend
*   **File Location**: [audit_logger.py](file:///c:/IMP/VIT/SY/SEM_2/EDI/NiyamAI-Proj-Code-Original/schema/audit_logger.py) and [audit_repository.py](file:///c:/IMP/VIT/SY/SEM_2/EDI/NiyamAI-Proj-Code-Original/schema/audit_repository.py)
*   **Description**: Writes structured execution and interception records to an index-optimized SQLite database (`audit.db`) through the `AuditRepository` pattern. Maintains a backward-compatible double-write append-only JSONLines file (`audit_log.jsonl`).
*   **Hash Chaining & Tamper-Evidence**: Implements a cryptographic hash chain mapping `prev_hash` and `current_hash` (aliased as `log_hash`) across application restarts, allowing automated integrity verification and tampering detection.

---

## Governance Validation Flow Sequence

The sequence below illustrates the validation flow coordinated by the `Interceptor` when a tool invocation is requested:

```mermaid
sequenceDiagram
    autonumber
    actor Agent as Autonomous Agent
    participant Interceptor as Interceptor (PEP)
    participant CFI as Control Flow Integrity
    participant Gate as ToolAuthorityGate (PDP)
    participant Runtime as Execution Runtime (PEP)
    participant Log as Audit Logger

    Agent->>Interceptor: Request tool execution (tool, payload)
    activate Interceptor
    Interceptor->>CFI: validate_step(tool)
    note over CFI: Verifies sequential order compliance
    CFI-->>Interceptor: Step Validated
    
    Interceptor->>Gate: validate_tool(tool)
    note over Gate: Checks allow/deny list of IntentContract
    Gate-->>Interceptor: Authorized (or throws block reason)
    
    Interceptor->>Gate: validate_schema(tool, payload)
    note over Gate: Validates parameters & rejects extra properties
    Gate-->>Interceptor: Schema Compliant (or throws block reason)
    
    note over Interceptor: Run zkML feature extraction, proving, & verification
    
    Interceptor->>Runtime: execute_governed(context, payload)
    activate Runtime
    note over Runtime: Enforces FSM state changes & timeout
    Runtime-->>Interceptor: Execution Output (or timeout/failure)
    deactivate Runtime
    
    Interceptor->>Log: log_event(status=EXECUTED)
    Interceptor-->>Agent: Return result
    deactivate Interceptor
```

---

## Execution Containment & Process Isolation Layer

To protect the host process from unverified tool behavior, NIYAM-AI implements an **Execution Containment Layer** structured as follows:

```mermaid
graph TD
    subgraph Execution Containment Layer
        Runtime[GovernedExecutionRuntime (Isolated Execution Runtime)]
        SandboxExec[Sandbox Executor (Implementation Layer)]
        SubprocExec[SubprocessSandboxExecutor (Process Isolation Layer - Preferred)]
        ThreadExec[ThreadSandboxExecutor (Fallback Containment)]

        Runtime --> SandboxExec
        SandboxExec --> SubprocExec
        SandboxExec --> ThreadExec
    end
```

### Process Isolation Layer
Tool execution is isolated from the parent interpreter using **process isolation**. The runtime spawns a separate OS process via Python's `multiprocessing` to isolate:
1.  **Memory Space**: Prevents tool callables from directly accessing or mutating global interpreter states, database connections, keys, or sealed contracts in the parent process.
2.  **Resource Containment**: Enables clean parent-directed termination (`.terminate()` / `.kill()`) if the execution exceeds the timeout limit, preventing lingering zombie execution threads in the host system.

### Execution State Transitions
The lifecycle of a single tool execution attempt is managed as a finite state machine (FSM) enforcing safe transition sequences:

```mermaid
stateDiagram-v2
    [*] --> PENDING
    PENDING --> RUNNING : EXECUTION_STARTED
    RUNNING --> COMPLETED : EXECUTION_COMPLETED
    RUNNING --> TIMED_OUT : EXECUTION_TIMEOUT (Thread fallback path)
    RUNNING --> TERMINATED : EXECUTION_TERMINATED (Subprocess path)
    RUNNING --> FAILED : EXECUTION_FAILED

    TIMED_OUT --> CLEANED_UP : CLEANUP_COMPLETED/FAILED
    FAILED --> CLEANED_UP : CLEANUP_COMPLETED/FAILED
    TERMINATED --> CLEANED_UP : CLEANUP_COMPLETED/FAILED

    COMPLETED --> [*]
    CLEANED_UP --> [*]
```

### Threat Model & Current Limitations
While the current Process Isolation Layer isolates memory and enables timeout termination, it does not constitute a full operating-system-level sandbox:

*   **Current Limitations**:
    *   *Shared OS Namespace*: The isolated subprocess still shares the host machine's network stack, local filesystem, and environment variables. If a malicious tool attempts disk I/O or network requests, standard process isolation does not block these OS-level calls automatically unless handled by OS permissions.
    *   *Serialization (Pickling) Constraints*: Callables must be pickleable to be passed to a subprocess. Local lambdas, dynamically generated nested helper functions, and unpickleable objects trigger fallback to `ThreadSandboxExecutor` (which runs in the parent memory space).
*   **Future Opportunities for Stronger Sandboxing**:
    *   *Virtualization*: Packaging tools in gVisor, WebAssembly (Wasm) runtimes, or MicroVMs (e.g., Firecracker) to restrict access to network, system calls, and the filesystem.
    *   *Subprocess Jail/Chroot*: Confining process filesystem root directories and running under unprivileged system users.
    *   **Serialization Upgrades**: Utilizing serialization frameworks like `dill` or `pathos` to decrease pickling failures.

---

## Audit Layer & SQLite Backend

To resolve the query limitations, linear scans, and performance bottlenecks of prototype JSONLines logs, NIYAM-AI implements a secure, database-backed **Audit Layer** designed around the **Audit Repository Pattern**.

```mermaid
graph TD
    UI[Frontend Streamlit View] --> GS[schema/governance_service.py]
    GS --> AR[schema/audit_repository.py - AuditRepository]
    IP[Interceptor / PEP] --> AL[schema/audit_logger.py - log_event]
    AL --> AR
    AR --> DB[(SQLite Database - audit.db)]
```

### 1. Audit Repository Pattern
All database interactions are centralized inside the `AuditRepository` class (located in [audit_repository.py](file:///c:/IMP/VIT/SY/SEM_2/EDI/NiyamAI-Proj-Code-Original/schema/audit_repository.py)). The rest of the application (e.g. frontend pages, metrics calculators, and logging gates) delegates queries and write calls directly to this class, preventing database logic leakage and SQL injection vulnerabilities.

### 2. Tamper-Evident Hash Chain
To ensure governance transparency and detect unauthorized modifications, the audit system creates a cryptographic ledger mapping each row to the preceding event:

```text
Event N-1
  └── [current_hash]
          │
          ▼  (linked as)
Event N
  ├── [prev_hash] = Event N-1 current_hash
  └── [current_hash] = SHA-256(prev_hash + JSON_payload(Event N))
```

* **Genesis Link**: When a new chain sequence begins, the `prev_hash` is initialized to `"0"`.
* **Hash Recalculation**: During verification, the system serializes each database record back into a dictionary (omitting database metadata such as `event_id` and the signature keys themselves), prepends the `prev_hash`, and recomputes the SHA-256 hash.

### 3. Chain Integrity Verification
The repository exposes a first-class security capability `verify_chain()` that inspects all events sequentially to validate:
1. **Chain Continuity**: Asserts that `event[n].current_hash` exactly matches `event[n+1].prev_hash`.
2. **Record Authenticity**: Independently recalculates the hash signature of each payload to detect single-record modifications or tampering.
3. **Anomalies Detection**: Reports deleted entries (missing links) and invalid hashes.

### 4. Migration Strategy
To transition from prototype jsonl files, the [migrate_jsonl_to_sqlite.py](file:///c:/IMP/VIT/SY/SEM_2/EDI/NiyamAI-Proj-Code-Original/migrate_jsonl_to_sqlite.py) utility parses the legacy `audit_log.jsonl` database, preserves all original timestamps and signatures exactly, and populates the SQLite tables. It flags syntax errors or structural anomalies without losing history.

---

## zkML Security Layer & Proof Lifecycle

NIYAM-AI verifies tool execution inputs using zero-knowledge Machine Learning (zkML). Since the model validation and proof pipeline are critical security subsystems, they are backed by a structured proof lifecycle state machine and strict fail-closed enforcement rules.

### 1. Proof State Machine (FSM)
The lifecycle of a single zkML proof and witness is managed as a finite state machine (FSM) using the `ProofState` states:

```mermaid
stateDiagram-v2
    [*] --> PROOF_PENDING
    
    PROOF_PENDING --> PROOF_GENERATING : Start proving
    PROOF_PENDING --> PROOF_FAILED : Write/file system failure
    PROOF_PENDING --> PROOF_MISSING : missing circuit/inputs
    PROOF_PENDING --> PROOF_INVALID : Malformed parameters

    PROOF_GENERATING --> PROOF_GENERATED : ezkl gen-witness + prove success
    PROOF_GENERATING --> PROOF_FAILED : subprocess crash/timeout

    PROOF_GENERATED --> PROOF_VERIFYING : Start verification
    PROOF_GENERATED --> PROOF_FAILED : File read/write failure

    PROOF_VERIFYING --> PROOF_VERIFIED : ezkl verify success
    PROOF_VERIFYING --> PROOF_FAILED : verify execution crash/timeout
    PROOF_VERIFYING --> PROOF_INVALID : invalid structure/VK signature mismatch
    PROOF_VERIFYING --> PROOF_MISSING : proof/witness file missing

    PROOF_VERIFIED --> [*]
    PROOF_FAILED --> [*]
    PROOF_INVALID --> [*]
    PROOF_MISSING --> [*]
```

### 2. Fail-Closed Execution Policy
To ensure that "No Valid Proof, No Execution" is strictly enforced, the interceptor and runtime implement fail-closed policies across multiple boundary conditions:
*   **Startup Validation**: During application/module startup, `validate_proof_environment()` runs checks on the environment before any execution can begin. If:
    1.  The `ezkl` binary utility is not available or executable in the system path,
    2.  Any required artifact file (`model.onnx`, `circuit.ezkl`, `settings.json`, `vk.key`, `pk.key`, `kzg.srs`) is missing or unreadable,
    3.  The cryptographic hash of `vk.key` does not match the hardcoded `TRUSTED_VK_HASH` value,
    The system shifts into `PROOF_ENVIRONMENT_INVALID` state, logs the failure, and **blocks all future tool executions** from starting.
*   **Structural Verification**: Before running cryptographic verification, `validate_proof_artifacts()` parses the JSON structure of both `proof.json` and `witness.json` to verify essential keys (like `instances`, `proof`, `inputs`, `outputs`) and rejects any malformed payload formats immediately, preventing potential parser vulnerabilities in the `ezkl` binary.
*   **Subprocess Environment Failures**: If subprocess invocations for `ezkl gen-witness` or `ezkl prove` crash or raise execution exceptions (e.g. out of memory, file access limits), the system immediately deletes any partially written or stale artifacts (like partial `witness.json` or `proof.json`) and halts execution.

### 3. Component Trust Boundaries
The following trust boundaries define how components rely on or verify each other:
1.  **Interceptor (PEP) -> Prover/Verifier**: The Interceptor treats the Prover and Verifier as untrusted runtime boundaries that could fail or yield invalid states. It wraps proving/verification calls, checks for validity reports, and enforces a default-deny block if any step is bypassed.
2.  **Verifier -> Host System (EZKL)**: The Verifier executes the `ezkl` CLI as a separate process. Before running the binary, the Verifier validates the structural inputs and verifies the checksum hash of the Verification Key (`vk.key`) to guarantee the binary is executing verification against the authentic compiled model constraints, rather than an arbitrary mock key.
3.  **Governance Service -> Interceptor**: Streamlit dashboard interfaces query metrics and load logs through the `GovernanceService` layer, separating UI rendering code from internal verification, cryptographic state checking, and database transaction lifecycles.
