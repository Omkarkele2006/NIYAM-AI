# NIYAM-AI

## Intent-Bound Verifiable AI Governance System

![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![ONNX](https://img.shields.io/badge/ONNX-Model_Runtime-005CED?style=for-the-badge&logo=onnx&logoColor=white)
![zkML](https://img.shields.io/badge/zkML-Verifiable_AI-9D4EDD?style=for-the-badge)
![EZKL](https://img.shields.io/badge/EZKL-Proof_System-00D1FF?style=for-the-badge)

NIYAM-AI is a futuristic AI governance and observability platform developed at **Vishwakarma Institute of Technology (VIT), Pune**. It explores how autonomous AI execution can be made intent-bound, cryptographically traceable, proof-aware, and operationally observable.

The platform combines **Intent Contracts**, **Tool Governance**, **zkML Proof Generation**, **Cryptographic Verification**, **Immutable Audit Logging**, **Real-time Governance Monitoring**, **Threat Analytics**, and **Proof Transparency** into a single research-grade prototype.

---

## Project Overview

Modern AI agents can trigger tools, access data, call APIs, execute transactions, and interact with external systems. This creates a governance challenge: how do we ensure that an AI system only performs actions aligned with the user's authorized intent?

NIYAM-AI addresses this problem by placing a governance boundary between the agent's proposed action and the actual execution layer.

Every governed action is:

1. Bound to an intent contract.
2. Checked against tool authority rules.
3. Converted into deterministic governance features.
4. Passed through a zkML proof pipeline.
5. Verified before execution.
6. Written into an append-only audit trail.
7. Displayed through a real-time observability dashboard.

The result is a practical prototype for **verifiable AI governance**, where AI execution is not only monitored but also cryptographically accountable.

---

## Key Features

- **Intent Contracts**  
  Session-bound contracts define allowed tools, forbidden tools, user task scope, and deterministic intent hashes.

- **Tool Governance**  
  Centralized tool authorization prevents unauthorized or forbidden actions from executing.

- **Control-Flow Integrity**  
  Expected execution sequences are validated before tool execution.

- **Cryptographic Action Hashing**  
  Each tool invocation is hashed using deterministic SHA-256 action hashing.

- **zkML Proof Generation**  
  Governance features are encoded into witness data and used to generate proof artifacts.

- **Cryptographic Verification**  
  Proof verification and verification-key integrity checks create a fail-safe execution boundary.

- **Immutable Audit Logging**  
  Governance events are appended to JSONL logs with hash-chain metadata.

- **Threat Analytics**  
  Streamlit dashboards expose blocked actions, tool activity, recent threat events, and verification coverage.

- **Proof Transparency**  
  Proof, witness, verification key, and audit evidence are made inspectable through the frontend.

---

## System Architecture

The architecture centers on a governance pipeline that intercepts AI tool execution requests before they reach the execution layer.

![NIYAM-AI System Architecture](frontend/assets/images/niyam_architecture.png)

### Architecture Layers

- **Agent Layer**: Accepts user prompts and proposes tool actions.
- **Intent Layer**: Creates sealed, hash-bound intent contracts.
- **Guardrail Layer**: Enforces control-flow and tool authorization.
- **zkML Layer**: Extracts features and generates proof artifacts.
- **Verification Layer**: Verifies proof integrity before execution.
- **Execution Layer**: Executes only governed and verified actions.
- **Audit Layer**: Records tamper-evident governance events.
- **Observability Layer**: Displays realtime metrics, proofs, threats, and logs.

---

## Governance Lifecycle

```text
Prompt
  -> Intent Contract
  -> Governance Validation
  -> Tool Gate
  -> zkML Feature Extraction
  -> Proof Generation
  -> Verification
  -> Secure Execution
  -> Immutable Audit Logging
  -> Frontend Observability
```

### Lifecycle Explanation

1. **Prompt**  
   A user or agent request enters the governance boundary.

2. **Intent Contract**  
   The requested task is bound to an allowed/forbidden tool policy.

3. **Governance Validation**  
   Control-flow integrity and policy constraints are checked.

4. **Tool Gate**  
   Unauthorized tools are blocked before reaching execution.

5. **zkML Feature Extraction**  
   ActionHash, IntentHash, tool identity, payload size, and security signals are converted into numeric model features.

6. **Proof Generation**  
   EZKL generates witness and proof artifacts for the model execution path.

7. **Verification**  
   Proof validity and verification-key integrity are checked.

8. **Secure Execution**  
   The tool executes only if governance and verification succeed.

9. **Immutable Audit Logging**  
   Every attempt is recorded in an append-only governance log.

10. **Frontend Observability**  
   Streamlit dashboards expose operational trust signals.

---

## zkML Pipeline

NIYAM-AI uses a lightweight ML-based governance model prepared for zkML verification.

### Pipeline Stages

- **Feature Extraction**  
  Converts governance metadata into deterministic numeric features.

- **Model Training**  
  A compact PyTorch model is trained on synthetic governance/action data.

- **ONNX Export**  
  The model is exported into an ONNX-compatible graph.

- **EZKL Circuit Preparation**  
  ONNX operators are adapted for EZKL-compatible proof generation.

- **Witness Generation**  
  Runtime input features are encoded into a witness file.

- **Proof Generation**  
  EZKL generates a cryptographic proof of model execution.

- **Proof Verification**  
  The proof is verified using the verification key and structured reference string.

- **Verification-Key Integrity**  
  The verification key is checked using SHA-256 hashing before proof verification.

---

## Frontend Observability Platform

The Streamlit frontend provides a cyber-governance dashboard for monitoring the entire platform.

### Pages

- **Home Dashboard**  
  High-level governance metrics powered by real audit logs.

- **Live Monitor**  
  Real-time operations dashboard with governance event stream, blocked action alerts, proof activity, and execution pipeline visualization.

- **Threat Analytics**  
  Blocked-action statistics, tool usage frequency, recent threat activity, and verification metrics.

- **Proof Explorer**  
  Proof metadata, witness visibility, verification status, verification key hash, and JSON inspectors.

- **Audit Logs**  
  Searchable and filterable audit table with action hashes, session filtering, proof status, and detailed metadata inspection.

- **Architecture**  
  Technical architecture overview for demos and evaluations.

- **About**  
  Research vision, mission, team, mentor, roadmap, and institution context.

- **Contact**  
  Project contact, repository, team directory, and collaboration details.

---

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | Streamlit, Plotly, HTML/CSS |
| Backend | Python |
| ML Model | PyTorch |
| Model Interchange | ONNX |
| Proof System | EZKL |
| Cryptography | SHA-256 |
| Logging | JSONL append-only audit logs |
| Governance | Intent contracts, tool gate, control-flow integrity |
| Observability | Real-time dashboards, proof explorer, audit analytics |

---

## Project Structure

```text
NIYAM-AI/
├── dashboard.py
├── main_demo.py
├── test_phase1.py
├── test_phase2.py
├── audit_log.jsonl
├── dataset.csv
├── model.pth
├── model.onnx
├── circuit.ezkl
├── input.json
├── witness.json
├── proof.json
├── pk.key
├── vk.key
├── kzg.srs
├── schema/
│   ├── intent_contract.py
│   ├── control_flow.py
│   ├── tool_gate.py
│   ├── action_hash.py
│   ├── interceptor.py
│   ├── zk_prover.py
│   ├── verifier.py
│   ├── audit_logger.py
│   ├── governance_service.py
│   └── ml/
│       ├── feature_extractor.py
│       ├── dataset_generator.py
│       ├── train_model.py
│       └── build_onnx.py
└── frontend/
    ├── Home.py
    ├── pages/
    │   ├── 1_Live_Monitor.py
    │   ├── 2_Threat_Analytics.py
    │   ├── 3_Proof_Explorer.py
    │   ├── 4_Audit_Logs.py
    │   ├── 5_Architecture.py
    │   ├── 6_About.py
    │   └── 7_Contact.py
    ├── components/
    │   └── cards.py
    ├── utils/
    │   ├── theme.py
    │   ├── chart_theme.py
    │   ├── audit_parser.py
    │   ├── proof_reader.py
    │   └── loaders.py
    └── assets/
        ├── css/
        │   └── cyber_theme.css
        └── images/
            └── niyam_architecture.png
```

---

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Omkarkele2006/NIYAM-AI.git
cd NIYAM-AI
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it:

```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

If a `requirements.txt` file is added:

```bash
pip install -r requirements.txt
```

Otherwise, install the core dependencies used by the current prototype:

```bash
pip install streamlit plotly pandas pydantic jsonschema torch onnx scikit-learn
```

EZKL must also be available in the runtime environment for proof generation and verification commands.

---

## Running the Streamlit Dashboard

Run the multipage frontend:

```bash
streamlit run frontend/Home.py
```

Then open the local Streamlit URL shown in the terminal.

Typical pages:

- `Home`
- `Live Monitor`
- `Threat Analytics`
- `Proof Explorer`
- `Audit Logs`
- `Architecture`
- `About`
- `Contact`

---

## Running the Governance Demo

The current backend demo can be executed with:

```bash
python test_phase2.py
```

This runs governed action simulations, updates audit logs, and interacts with the proof pipeline where the local EZKL environment is available.

---

## Governance Workflow

At runtime, a governed action flows through:

```text
schema/interceptor.py
  -> schema/action_hash.py
  -> schema/control_flow.py
  -> schema/tool_gate.py
  -> schema/ml/feature_extractor.py
  -> schema/zk_prover.py
  -> schema/verifier.py
  -> schema/audit_logger.py
```

The Streamlit frontend should interact with backend state through:

```text
schema/governance_service.py
```

Frontend data utilities:

```text
frontend/utils/audit_parser.py
frontend/utils/proof_reader.py
frontend/utils/chart_theme.py
```

This keeps the dashboard decoupled from low-level security and proof-generation internals.

---

## Screenshots

Add screenshots here after final UI capture.

### Home Dashboard

```text
screenshots/home_dashboard.png
```

### Live Monitor

```text
screenshots/live_monitor.png
```

### Threat Analytics

```text
screenshots/threat_analytics.png
```

### Proof Explorer

```text
screenshots/proof_explorer.png
```

### Audit Logs

```text
screenshots/audit_logs.png
```

---

## Future Roadmap

- Blockchain verifier integration.
- Smart contract based proof verification.
- Decentralized governance audit anchoring.
- Multi-agent governance sessions.
- Cloud-scale deployment of proof and monitoring services.
- Stronger model calibration and threat datasets.
- Proof-linked audit log explorer.
- Enterprise SIEM and compliance integrations.
- Role-based dashboard access.
- Policy authoring interface for intent contracts.

---

## Team

| Name | Contribution |
|---|---|
| **Om Karkele** | Full Stack Architecture, Governance Engine Integration, Frontend Observability |
| **Aditya Katkar** | zkML Pipeline, Proof Verification, Security Logic |
| **Yash Kashid** | Audit Analytics, Threat Monitoring, Visualization |
| **Kartik Mandhane** | UI Engineering, Streamlit Components, System Integration |

---

## Guide and Mentor

**Prof. Manisha More**  
Assistant Professor  
Vishwakarma Institute of Technology, Pune

---

## Institution

**Vishwakarma Institute of Technology (VIT), Pune**  
Computer Engineering Department  
SY CS F18

---

## License and Future Work

This repository is currently presented as an academic research and engineering prototype for EDI evaluation, technical demonstration, and continued development.

A formal open-source license can be added before public reuse or external contribution.

Future work will focus on stronger proof-system integration, decentralized verification, enterprise deployment patterns, improved governance datasets, and production-grade audit integrity.

