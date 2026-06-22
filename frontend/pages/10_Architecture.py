from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st


FRONTEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = FRONTEND_ROOT.parent

for path in (REPO_ROOT, FRONTEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from components.cards import cyber_card, metric_card, status_badge
from utils.theme import configure_page, load_global_css, section_title, page_header


ARCHITECTURE_IMAGE = FRONTEND_ROOT / "assets" / "images" / "niyam_architecture.png"


def _pipeline_stage(label: str, detail: str, color: str = "#22D3EE") -> str:
    """Return one compact lifecycle stage for the architecture walkthrough."""

    return f"""
<div style="flex:1; min-width:150px; background:var(--bg-card); border:1px solid {color}22; border-top:2px solid {color}; border-radius:10px; padding:1rem; min-height:110px;">
<div style="color:{color}; font-weight:600; font-size:0.88rem;">{label}</div>
<div style="color:#9AA3B2; font-size:0.78rem; line-height:1.45; margin-top:0.5rem;">{detail}</div>
</div>
"""


def _module_card(module_name: str, responsibility: str, signal: str) -> None:
    """Render a backend module relationship card."""

    cyber_card(
        module_name,
        f"""
        Responsibility: {responsibility}<br>
        Governance signal: {signal}
        """,
        min_height="190px",
    )


configure_page("Architecture | NIYAM-AI")
load_global_css()

page_header(
    "System Architecture",
    "NIYAM-AI Verifiable AI Governance Platform — component map and execution lifecycle",
    badge_label="GOVERNANCE PLATFORM",
    badge_kind="purple",
)

hero_col1, hero_col2, hero_col3, hero_col4 = st.columns(4)

with hero_col1:
    metric_card("Governance Core", "Intent", "Contracts and policy binding", "normal")

with hero_col2:
    metric_card("Trust Layer", "zkML", "Proof-backed model execution", "success")

with hero_col3:
    metric_card("Audit Model", "Hash Chain", "Tamper-evident records", "warning")

with hero_col4:
    metric_card("Frontend", "SOC View", "Realtime observability", "danger")

st.markdown("<br>", unsafe_allow_html=True)

intro_col1, intro_col2 = st.columns([1.35, 1])

with intro_col1:
    cyber_card(
        "Project Context",
        """
        NIYAM-AI is a Verifiable AI Governance Platform developed at VIT Pune.
        It combines Intent Contracts, Tool Governance, zkML Proof Generation,
        Cryptographic Verification, Immutable Audit Logging, and Real-time
        Governance Monitoring into one execution-control architecture.
        """,
        min_height="250px",
    )

with intro_col2:
    cyber_card(
        "Project Guide",
        """
        Prof. Manisha More<br>
        Assistant Professor<br>
        VIT Pune<br><br>
        Built for technical demos, EDI evaluations, research discussions,
        and enterprise AI governance walkthroughs.
        """,
        min_height="250px",
    )

section_title("SYSTEM ARCHITECTURE OVERVIEW")

if ARCHITECTURE_IMAGE.exists():
    st.image(str(ARCHITECTURE_IMAGE), use_container_width=True)
else:
    cyber_card(
        "Architecture Diagram Missing",
        f"Expected image not found at: {ARCHITECTURE_IMAGE}",
        min_height="180px",
    )

st.markdown("<br>", unsafe_allow_html=True)

layer_col1, layer_col2, layer_col3 = st.columns(3)

with layer_col1:
    cyber_card(
        "Agent Layer",
        """
        Receives user prompts and proposes tool actions. This layer is treated
        as untrusted until its requested action is bound to an intent contract,
        hashed, validated, proven, verified, and logged.
        """,
        min_height="260px",
    )

with layer_col2:
    cyber_card(
        "Guardrail Layer",
        """
        Enforces intent validation, control-flow sequencing, and tool
        authorization. It blocks forbidden tools and unexpected execution paths
        before actions reach the zkML proof pipeline.
        """,
        min_height="260px",
    )

with layer_col3:
    cyber_card(
        "Trust Boundary",
        """
        Separates proposed AI behavior from approved execution. The boundary is
        crossed only after governance validation, cryptographic proof generation,
        proof verification, and audit capture complete successfully.
        """,
        min_height="260px",
    )

layer_col4, layer_col5, layer_col6 = st.columns(3)

with layer_col4:
    cyber_card(
        "zkML Proof Pipeline",
        """
        Converts intent-bound features into witness data, generates a zkML proof
        with EZKL, and makes ML decision integrity observable without trusting
        opaque runtime claims.
        """,
        min_height="260px",
    )

with layer_col5:
    cyber_card(
        "Verification Layer",
        """
        Verifies generated proofs against the verification key and validates VK
        integrity through SHA-256 hashing before execution is considered safe.
        """,
        min_height="260px",
    )

with layer_col6:
    cyber_card(
        "Append-Only Audit Logging",
        """
        Records session identifiers, intent hashes, action hashes, proof state,
        verification state, status, reason, and hash-chain metadata for forensic
        governance traceability.
        """,
        min_height="260px",
    )

section_title("HIGH-LEVEL GOVERNANCE LIFECYCLE")

lifecycle_html = f"""
<div style="display:flex; flex-wrap:wrap; gap:0.75rem; align-items:stretch; margin-bottom:1.2rem;">
{_pipeline_stage('Prompt', 'User request enters the governance perimeter.', '#22D3EE')}
{_pipeline_stage('Intent Contract', 'Allowed and forbidden capabilities are bound to a session.', '#10B981')}
{_pipeline_stage('Governance Validation', 'Control flow and intent constraints are checked.', '#F59E0B')}
{_pipeline_stage('Tool Gate', 'Requested tool is authorized or blocked.', '#F43F5E')}
{_pipeline_stage('zkML Features', 'ActionHash, IntentHash, tool, and payload signals become model inputs.', '#818CF8')}
{_pipeline_stage('Proof Generation', 'EZKL witness and proof artifacts are produced.', '#22D3EE')}
{_pipeline_stage('Verification', 'Proof and verification key integrity are checked.', '#10B981')}
{_pipeline_stage('Secure Execution', 'Only verified governed actions execute.', '#F59E0B')}
{_pipeline_stage('Immutable Audit', 'Governance outcome is written to the audit trail.', '#22D3EE')}
{_pipeline_stage('Observability', 'Frontend pages expose operational trust signals.', '#818CF8')}
</div>
"""
st.markdown(lifecycle_html, unsafe_allow_html=True)

lifecycle_rows = [
    {"stage": "Prompt", "order": 1, "domain": "Agent"},
    {"stage": "Intent Contract", "order": 2, "domain": "Guardrail"},
    {"stage": "Governance Validation", "order": 3, "domain": "Guardrail"},
    {"stage": "Tool Gate", "order": 4, "domain": "Guardrail"},
    {"stage": "zkML Feature Extraction", "order": 5, "domain": "Proof"},
    {"stage": "Proof Generation", "order": 6, "domain": "Proof"},
    {"stage": "Verification", "order": 7, "domain": "Trust"},
    {"stage": "Secure Execution", "order": 8, "domain": "Execution"},
    {"stage": "Immutable Audit Logging", "order": 9, "domain": "Audit"},
    {"stage": "Frontend Observability", "order": 10, "domain": "Observability"},
]

fig_lifecycle = px.scatter(
    lifecycle_rows,
    x="order",
    y=["Governance Flow"] * len(lifecycle_rows),
    color="domain",
    text="stage",
    title="Prompt to Verifiable Execution Flow",
    labels={"order": "Execution Order", "y": ""},
    color_discrete_sequence=["#22D3EE", "#10B981", "#F59E0B", "#F43F5E", "#818CF8"],
)
fig_lifecycle.update_traces(marker_size=18, textposition="top center")
fig_lifecycle.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#E6E9EF",
    height=320,
    yaxis={"visible": False},
)
st.plotly_chart(fig_lifecycle, use_container_width=True)

mod_col1, mod_col2, mod_col3, mod_col4 = st.columns(4)

with mod_col1:
    _module_card(
        "interceptor.py",
        "Central policy enforcement point for all governed actions.",
        "ActionHash, proof, verification, audit status",
    )

with mod_col2:
    _module_card("intent_contract.py", "Defines session-bound allowed and forbidden tool policies.", "IntentHash and sealed policy identity")

with mod_col3:
    _module_card("control_flow.py", "Validates expected tool execution sequence.", "Control-flow integrity")

with mod_col4:
    _module_card("tool_gate.py", "Authorizes tools against the sealed intent contract.", "Allowed/forbidden tool decision")

mod_col5, mod_col6, mod_col7, mod_col8 = st.columns(4)

with mod_col5:
    _module_card("action_hash.py", "Creates deterministic cryptographic hashes of tool requests.", "ActionHash")

with mod_col6:
    _module_card("zk_prover.py", "Writes input, generates witness data, and produces EZKL proofs.", "proof.json and witness.json")

with mod_col7:
    _module_card("verifier.py", "Checks VK integrity and verifies generated zkML proofs.", "verification result")

with mod_col8:
    _module_card("audit_logger.py", "Appends governance events with hash-chain metadata.", "tamper-evident audit trail")

section_title("ZKML PIPELINE")

zk_col1, zk_col2 = st.columns([1, 1])

with zk_col1:
    cyber_card(
        "Proof Construction Flow",
        """
        Feature extraction converts ActionHash, IntentHash, tool encoding,
        payload size, high-risk indicators, forbidden-tool signals, harmful text,
        and injection patterns into deterministic numeric features.<br><br>
        The trained PyTorch model is exported to ONNX, converted into an
        EZKL-compatible graph, and compiled into a circuit for witness and proof
        generation.
        """,
        min_height="360px",
    )

with zk_col2:
    cyber_card(
        "Verification Flow",
        """
        EZKL generates witness data from the feature vector, produces proof.json,
        and verifies it using vk.key and the structured reference string.<br><br>
        The verification layer also checks the SHA-256 hash of the verification
        key, creating a fail-safe boundary against proof or key tampering.
        """,
        min_height="360px",
    )

section_title("FRONTEND OBSERVABILITY LAYER")

front_col1, front_col2, front_col3, front_col4, front_col5 = st.columns(5)

with front_col1:
    cyber_card("Home Dashboard", "Executive metrics for total actions, executed actions, blocked actions, and verified proofs.", min_height="230px")

with front_col2:
    cyber_card("Live Monitor", "Realtime operations stream, alerts, proof activity, and execution pipeline health.", min_height="230px")

with front_col3:
    cyber_card("Threat Analytics", "Blocked action trends, tool usage, recent threat activity, and verification coverage.", min_height="230px")

with front_col4:
    cyber_card("Audit Logs", "Searchable governance event records with filters, hashes, proof state, and metadata inspection.", min_height="230px")

with front_col5:
    cyber_card("Proof Explorer", "Proof, witness, verification key, artifact status, and JSON observability for zkML evidence.", min_height="230px")

section_title("SECURITY LAYERS")

security_rows = [
    {"layer": "Intent Validation", "coverage": 100, "domain": "Policy"},
    {"layer": "Tool Authorization", "coverage": 100, "domain": "Control"},
    {"layer": "Proof Verification", "coverage": 100, "domain": "Cryptography"},
    {"layer": "Hash-Chain Audit Integrity", "coverage": 100, "domain": "Audit"},
    {"layer": "Governance Enforcement", "coverage": 100, "domain": "Runtime"},
    {"layer": "Immutable Logging", "coverage": 100, "domain": "Forensics"},
]

fig_security = px.bar(
    security_rows,
    x="coverage",
    y="layer",
    color="domain",
    orientation="h",
    title="Defense-in-Depth Governance Layers",
    labels={"coverage": "Implemented Layer", "layer": "Security Layer"},
    color_discrete_sequence=["#22D3EE", "#10B981", "#F59E0B", "#F43F5E", "#818CF8"],
)
fig_security.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#E6E9EF",
    height=380,
    xaxis={"visible": False},
)
st.plotly_chart(fig_security, use_container_width=True)

tech_col1, tech_col2, tech_col3, tech_col4 = st.columns(4)

section_title("TEAM")

team_col1, team_col2 = st.columns([1, 1])

with team_col1:
    cyber_card(
        "Engineering Contributions",
        """
        Om Karkele — Full Stack Architecture, Governance Engine Integration, Frontend Observability<br><br>
        Aditya Katkar — zkML Pipeline, Proof Verification, Security Logic
        """,
        min_height="250px",
    )

with team_col2:
    cyber_card(
        "Analytics and Interface Contributions",
        """
        Yash Kashid — Audit Analytics, Threat Monitoring, Visualization<br><br>
        Kartik Mandhane — UI Engineering, Streamlit Components, System Integration
        """,
        min_height="250px",
    )
