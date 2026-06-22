"""
NIYAM-AI — Home / Landing Page
Enterprise Governance Operations Console
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from schema.governance_service import get_system_metrics
from utils.theme import (
    configure_page,
    load_global_css,
    page_header,
    section_title,
)
from components.cards import metric_card, cyber_card, status_badge


# =========================================================
# PAGE CONFIG
# =========================================================

configure_page("NIYAM-AI — Governance Console")


# =========================================================
# PAGE HEADER
# =========================================================

page_header(
    "NIYAM-AI",
    "Intent-Bound Verifiable AI Governance Platform · zkML-Powered · Immutable Audit",
    badge_label="SYSTEM ACTIVE",
    badge_kind="success",
)


# =========================================================
# SYSTEM METRICS
# =========================================================

metrics = get_system_metrics()

section_title("PLATFORM METRICS")

col1, col2, col3, col4 = st.columns(4)

with col1:
    metric_card(
        "Total Audited Actions",
        str(metrics["total_actions"]),
        "Governance audit records",
        "accent",
    )

with col2:
    metric_card(
        "Executed Actions",
        str(metrics["executed_actions"]),
        "Proof-verified executions",
        "success",
    )

with col3:
    metric_card(
        "Blocked Actions",
        str(metrics["blocked_actions"]),
        "Policy or proof rejections",
        "danger",
    )

with col4:
    metric_card(
        "Verified Proof Events",
        str(metrics["historical_verified_proof_events"]),
        "Historical audited verifications",
        "purple",
    )


# =========================================================
# PLATFORM OVERVIEW
# =========================================================

st.markdown("<br>", unsafe_allow_html=True)
section_title("PLATFORM OVERVIEW")

col1, col2 = st.columns([1.3, 1])

with col1:
    cyber_card(
        "Intent-Bound AI Security",
        """
        NIYAM-AI is an enterprise AI governance platform combining Intent Contracts,
        ML-based threat detection, and Zero-Knowledge Proofs to ensure safe,
        cryptographically verifiable AI execution.<br><br>

        Every prompt passes through a sealed Intent Contract, CFI validation,
        tool authority gating, and a real EZKL zkML proof before execution is
        permitted. All decisions are recorded in an immutable SHA-256 hash-chained
        audit ledger.
        """,
        min_height="280px",
    )

with col2:
    cyber_card(
        "Core Capabilities",
        """
        <b style="color:#22D3EE;">→</b> Intent Contract Enforcement<br><br>
        <b style="color:#22D3EE;">→</b> AI Tool Authority Governance<br><br>
        <b style="color:#10B981;">→</b> ML-Based Threat Detection<br><br>
        <b style="color:#818CF8;">→</b> zkML Proof Generation (EZKL)<br><br>
        <b style="color:#818CF8;">→</b> Cryptographic Verification<br><br>
        <b style="color:#F59E0B;">→</b> Immutable Audit Chain
        """,
        min_height="280px",
    )


# =========================================================
# SYSTEM HEALTH SNAPSHOT
# =========================================================

section_title("DEPLOYMENT")

col_a, col_b, col_c = st.columns(3)

with col_a:
    cyber_card(
        "Proof Runtime",
        """
        <b>Engine:</b> EZKL v0.x (Ubuntu/WSL)<br><br>
        <b>Status:</b> <span style="color:#10B981;">OPERATIONAL</span><br><br>
        <b>Circuit:</b> Intent Risk Classifier (ONNX)<br><br>
        <b>Proving scheme:</b> KZG commitments
        """,
        min_height="180px",
    )

with col_b:
    artifacts = metrics.get("artifacts", {})
    proof_ok = artifacts.get("proof", {}).get("exists", False)
    witness_ok = artifacts.get("witness", {}).get("exists", False)
    cyber_card(
        "Artifact Status",
        f"""
        <b>proof.json:</b> {'<span style="color:#10B981;">PRESENT</span>' if proof_ok else '<span style="color:#F43F5E;">MISSING</span>'}<br><br>
        <b>witness.json:</b> {'<span style="color:#10B981;">PRESENT</span>' if witness_ok else '<span style="color:#F43F5E;">MISSING</span>'}<br><br>
        <b>Execution scoping:</b> Isolated per-run IDs<br><br>
        <b>Retention:</b> All artifacts retained
        """,
        min_height="180px",
    )

with col_c:
    chain_status = metrics.get("chain_status", "UNKNOWN")
    chain_color = "#10B981" if chain_status == "VALID" else "#F43F5E"
    cyber_card(
        "Audit Ledger",
        f"""
        <b>Chain integrity:</b> <span style="color:{chain_color};">{chain_status}</span><br><br>
        <b>Total events:</b> {metrics['total_actions']}<br><br>
        <b>Hash algorithm:</b> SHA-256 chained<br><br>
        <b>Storage:</b> SQLite (append-only)
        """,
        min_height="180px",
    )


# =========================================================
# FOOTER
# =========================================================

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div style="
        text-align:center;
        color:#4B5563;
        padding-bottom:1.5rem;
        font-size:0.78rem;
        letter-spacing:0.04em;
        border-top:1px solid #1F2430;
        padding-top:1rem;
        margin-top:0.5rem;
    ">
        NIYAM-AI &nbsp;·&nbsp; Enterprise Governance Operations Console
        &nbsp;·&nbsp; zkML-Powered &nbsp;·&nbsp; Commit 12
    </div>
    """,
    unsafe_allow_html=True,
)
