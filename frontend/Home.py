import streamlit as st

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

section_title("SYSTEM METRICS")


col1, col2, col3, col4 = st.columns(4)


with col1:

    metric_card(
        "Verified Executions",
        "12,482",
        "+12.8% this week",
        "success"
    )


with col2:

    metric_card(
        "Threats Blocked",
        "1,294",
        "+4.2% today",
        "danger"
    )


with col3:

    metric_card(
        "zk Proofs Generated",
        "8,104",
        "Realtime pipeline",
        "normal"
    )


with col4:

    metric_card(
        "Avg Verification",
        "0.82s",
        "Optimized",
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