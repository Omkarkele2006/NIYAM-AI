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
from utils.theme import configure_page, load_global_css, section_title


configure_page("About | NIYAM-AI")
load_global_css()

section_title("ABOUT NIYAM-AI")
status_badge("INTENT-BOUND VERIFIABLE AI GOVERNANCE SYSTEM", "info")

hero_col1, hero_col2, hero_col3, hero_col4 = st.columns(4)

with hero_col1:
    metric_card("Governance", "Intent", "Policy-bound execution", "normal")

with hero_col2:
    metric_card("Proofs", "zkML", "Verifiable inference", "success")

with hero_col3:
    metric_card("Integrity", "SHA-256", "Cryptographic traceability", "warning")

with hero_col4:
    metric_card("Monitoring", "Realtime", "Operational observability", "danger")

st.markdown("<br>", unsafe_allow_html=True)

overview_col1, overview_col2 = st.columns([1.35, 1])

with overview_col1:
    cyber_card(
        "Project Identity",
        """
        NIYAM-AI is a Verifiable AI Governance Platform developed at
        Vishwakarma Institute of Technology, Pune. It combines Intent Contracts,
        Tool Governance, zkML Proof Generation, Cryptographic Verification,
        Immutable Audit Logging, and Real-time Governance Monitoring.
        """,
        min_height="250px",
    )

with overview_col2:
    cyber_card(
        "Tagline",
        """
        Intent-Bound Verifiable AI Governance System<br><br>
        Built for secure AI execution, accountable autonomy, and proof-backed
        trust in intelligent systems.
        """,
        min_height="250px",
    )

section_title("PROJECT VISION")

vision_col1, vision_col2, vision_col3 = st.columns(3)

with vision_col1:
    cyber_card(
        "Why AI Governance Matters",
        """
        Autonomous AI systems increasingly make decisions that trigger tools,
        transactions, data access, and external actions. Governance is needed to
        ensure that these actions remain aligned with authorized intent.
        """,
        min_height="270px",
    )

with vision_col2:
    cyber_card(
        "Need for Verifiable AI",
        """
        Trust cannot rely only on runtime claims. NIYAM-AI treats verification as
        a first-class requirement by connecting model decisions to cryptographic
        proof artifacts and auditable execution records.
        """,
        min_height="270px",
    )

with vision_col3:
    cyber_card(
        "Transparent Trust Boundaries",
        """
        The platform creates a clear boundary between proposed AI behavior and
        approved execution. Every action must pass governance checks, proof
        verification, and audit logging.
        """,
        min_height="270px",
    )

section_title("MISSION STATEMENT")

mission_col1, mission_col2 = st.columns([1, 1])

with mission_col1:
    cyber_card(
        "Secure AI Execution",
        """
        NIYAM-AI aims to prevent unsafe autonomous actions by enforcing intent
        contracts, tool permissions, and execution flow validation before any
        governed tool call is allowed to proceed.
        """,
        min_height="260px",
    )

with mission_col2:
    cyber_card(
        "Enterprise Trust",
        """
        The mission is to make AI execution explainable, verifiable, and
        audit-ready through proof-backed verification, immutable logs, and
        operational observability for governance teams.
        """,
        min_height="260px",
    )

section_title("PLATFORM CAPABILITIES")

capabilities = [
    {"capability": "Intent Contracts", "domain": "Policy", "value": 95},
    {"capability": "Tool Governance", "domain": "Runtime", "value": 92},
    {"capability": "zkML Proofs", "domain": "Cryptography", "value": 88},
    {"capability": "Verification Pipelines", "domain": "Trust", "value": 90},
    {"capability": "Immutable Audit Logging", "domain": "Audit", "value": 94},
    {"capability": "Real-time Monitoring", "domain": "Observability", "value": 91},
]

fig_capabilities = px.bar(
    capabilities,
    x="value",
    y="capability",
    color="domain",
    orientation="h",
    title="Governance Capability Map",
    labels={"value": "Capability Coverage", "capability": "Capability"},
    color_discrete_sequence=["#00D1FF", "#00FF88", "#FFC857", "#FF3B5C", "#9D4EDD"],
)
fig_capabilities.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#E6F1FF",
    height=360,
    xaxis={"visible": False},
)
st.plotly_chart(fig_capabilities, use_container_width=True)

cap_col1, cap_col2, cap_col3 = st.columns(3)

with cap_col1:
    cyber_card("Intent Contracts", "Session-bound policies define what an AI agent is allowed and forbidden to execute.", min_height="210px")

with cap_col2:
    cyber_card("Tool Governance", "Tool calls pass through centralized control-flow and authority checks before execution.", min_height="210px")

with cap_col3:
    cyber_card("zkML Proofs", "ML-based governance decisions are connected to proof artifacts for verifiable execution.", min_height="210px")

cap_col4, cap_col5, cap_col6 = st.columns(3)

with cap_col4:
    cyber_card("Verification Pipelines", "Proofs and verification key integrity are checked before trust-sensitive execution.", min_height="210px")

with cap_col5:
    cyber_card("Immutable Audit Logging", "Governance events are captured as append-only records with cryptographic hashes.", min_height="210px")

with cap_col6:
    cyber_card("Real-time Monitoring", "Streamlit observability pages expose metrics, alerts, proof state, and audit trails.", min_height="210px")

section_title("INNOVATION AND RESEARCH FOCUS")

research_col1, research_col2 = st.columns([1, 1])

with research_col1:
    cyber_card(
        "Cryptographic Governance",
        """
        NIYAM-AI explores how cryptographic verification can make AI governance
        stronger than conventional logging. Action hashes, intent hashes,
        verification key checks, and proof artifacts create a measurable trust
        fabric around autonomous behavior.
        """,
        min_height="310px",
    )

with research_col2:
    cyber_card(
        "Deterministic Execution Validation",
        """
        The platform focuses on deterministic, reproducible validation:
        structured feature extraction, ONNX-compatible model conversion,
        witness generation, proof verification, and append-only audit trails
        that support forensic inspection.
        """,
        min_height="310px",
    )

highlight_col1, highlight_col2, highlight_col3 = st.columns(3)

with highlight_col1:
    cyber_card("zkML Integration", "Bridges machine learning governance with zero-knowledge proof systems.", min_height="210px")

with highlight_col2:
    cyber_card("Governance Observability", "Makes proof state, blocked actions, audit events, and execution health visible.", min_height="210px")

with highlight_col3:
    cyber_card("Append-Only Audit Trails", "Provides a foundation for tamper-evident execution accountability.", min_height="210px")

section_title("TEAM")

team_col1, team_col2 = st.columns(2)

with team_col1:
    cyber_card(
        "Om Karkele",
        """
        Role: Full Stack Architecture<br>
        Contribution Area: Governance Engine Integration, Frontend Observability,
        architecture coordination, and Streamlit platform structure.
        """,
        min_height="250px",
    )

with team_col2:
    cyber_card(
        "Aditya Katkar",
        """
        Role: zkML Pipeline<br>
        Contribution Area: Proof Verification, Security Logic, model-to-proof
        integration, and cryptographic verification workflow.
        """,
        min_height="250px",
    )

team_col3, team_col4 = st.columns(2)

with team_col3:
    cyber_card(
        "Yash Kashid",
        """
        Role: Audit Analytics<br>
        Contribution Area: Threat Monitoring, Visualization, audit insights,
        dashboard analytics, and operational governance metrics.
        """,
        min_height="250px",
    )

with team_col4:
    cyber_card(
        "Kartik Mandhane",
        """
        Role: UI Engineering<br>
        Contribution Area: Streamlit Components, System Integration, page
        layouts, interface consistency, and cyber-themed experience design.
        """,
        min_height="250px",
    )

section_title("GUIDE AND MENTOR")

guide_col1, guide_col2 = st.columns([1, 1])

with guide_col1:
    cyber_card(
        "Prof. Manisha More",
        """
        Assistant Professor<br>
        Vishwakarma Institute of Technology, Pune<br><br>
        Academic guide and mentor for the NIYAM-AI project.
        """,
        min_height="230px",
    )

with guide_col2:
    cyber_card(
        "Mentorship Focus",
        """
        The project is guided toward practical engineering, research relevance,
        secure system thinking, and clear technical communication for EDI
        evaluation and viva presentation.
        """,
        min_height="230px",
    )

section_title("FUTURE ROADMAP")

roadmap_col1, roadmap_col2, roadmap_col3 = st.columns(3)

with roadmap_col1:
    cyber_card(
        "Blockchain Verification",
        """
        Integrate proof verification with blockchain networks and smart
        contracts for decentralized trust and public auditability.
        """,
        min_height="230px",
    )

with roadmap_col2:
    cyber_card(
        "Decentralized Governance",
        """
        Extend governance policy enforcement across distributed agents,
        organizations, and shared trust domains.
        """,
        min_height="230px",
    )

with roadmap_col3:
    cyber_card(
        "Cloud-Scale Deployment",
        """
        Package the governance engine, dashboards, and proof services for
        scalable enterprise environments.
        """,
        min_height="230px",
    )

roadmap_col4, roadmap_col5, roadmap_col6 = st.columns(3)

with roadmap_col4:
    cyber_card("Smart Contract Verification", "Anchor proof outcomes and audit checkpoints into programmable verification contracts.", min_height="220px")

with roadmap_col5:
    cyber_card("Multi-Agent Governance", "Support multiple governed agents with isolated intent contracts and shared audit observability.", min_height="220px")

with roadmap_col6:
    cyber_card("Enterprise Integrations", "Connect NIYAM-AI to enterprise workflows, policy engines, SIEM tools, and compliance systems.", min_height="220px")

section_title("INSTITUTION")

institution_col1, institution_col2 = st.columns([1, 1])

with institution_col1:
    cyber_card(
        "Vishwakarma Institute of Technology",
        """
        Vishwakarma Institute of Technology (VIT), Pune<br>
        Computer Engineering Department<br>
        SY CS F18
        """,
        min_height="220px",
    )

with institution_col2:
    cyber_card(
        "Governance Philosophy",
        """
        NIYAM-AI is built around a simple principle: autonomous AI should not
        merely be powerful; it should be governed, verifiable, explainable, and
        accountable at every execution boundary.
        """,
        min_height="220px",
    )
