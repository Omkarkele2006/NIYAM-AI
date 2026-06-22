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
    cyber_header,
    section_title
)

from components.cards import (
    metric_card,
    cyber_card,
    status_badge
)


# =========================================================
# PAGE CONFIG
# =========================================================

configure_page("NIYAM-AI")


# =========================================================
# LOAD GLOBAL CSS
# =========================================================



# =========================================================
# HERO SECTION
# =========================================================

cyber_header(
    "NIYAM-AI",
    "Intent-Bound Verifiable AI Governance System"
)


status_badge(
    "SYSTEM ACTIVE",
    "success"
)


st.markdown("<br>", unsafe_allow_html=True)


# =========================================================
# METRICS SECTION
# =========================================================

metrics = get_system_metrics()

section_title("SYSTEM METRICS")


col1, col2, col3, col4 = st.columns(4)


with col1:

    metric_card(
        "Total Actions (Audited)",
        str(metrics["total_actions"]),
        "Audit log records",
        "success"
    )


with col2:

    metric_card(
        "Executed Actions (Audited)",
        str(metrics["executed_actions"]),
        "Governed executions",
        "danger"
    )


with col3:

    metric_card(
        "Blocked Actions (Audited)",
        str(metrics["blocked_actions"]),
        "Policy or proof blocks",
        "normal"
    )


with col4:

    metric_card(
        "Historical Proof Events (Historical)",
        str(metrics["historical_verified_proof_events"]),
        "Audit records with verification=True (see Proof Explorer for live status)",
        "warning"
    )
# =========================================================
# OVERVIEW SECTION
# =========================================================

section_title("PLATFORM OVERVIEW")


col1, col2 = st.columns([1.3, 1])


with col1:

    cyber_card(
        "Intent-Bound AI Security",
        """
        NIYAM-AI is a next-generation AI governance platform
        that combines Intent Contracts, Machine Learning,
        cryptographic verification, and Zero-Knowledge Proofs
        to ensure safe and verifiable AI execution.

        The platform monitors prompts, validates actions,
        generates zkML proofs, verifies execution integrity,
        and maintains immutable audit traces.
        """,
        min_height="320px"
    )


with col2:

    cyber_card(
        "Core Capabilities",
        """
        • Intent Contract Enforcement<br><br>

        • AI Tool Governance<br><br>

        • ML-Based Threat Detection<br><br>

        • zkML Proof Generation<br><br>

        • Cryptographic Verification<br><br>

        • Immutable Audit Logging
        """,
        min_height="320px"
    )


# =========================================================
# FOOTER
# =========================================================

st.markdown("<br><br>", unsafe_allow_html=True)

st.markdown(
    """
    <div style="
        text-align:center;
        color:#93A4C3;
        padding-bottom:2rem;
        font-size:0.9rem;
    ">
        NIYAM-AI • Verifiable AI Governance Platform
    </div>
    """,
    unsafe_allow_html=True
)
