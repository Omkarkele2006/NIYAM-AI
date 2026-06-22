"""
NIYAM-AI — Governance Control Center
Unified security visibility, policy verification, and audit integrity metrics.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from schema.governance_service import get_dashboard_overview_metrics
from utils.theme import configure_page, load_global_css, page_header, section_title
from components.cards import metric_card, cyber_card, status_badge

configure_page("Governance Overview | NIYAM-AI")
load_global_css()

page_header(
    "Governance Control Center",
    "Unified security visibility, policy verification, and audit integrity metrics",
    badge_label="MONITORING ACTIVE",
    badge_kind="success",
)

metrics = get_dashboard_overview_metrics()

# ── 4-column KPI strip ──────────────────────────────────────
section_title("SYSTEM HEALTH")

col1, col2, col3, col4 = st.columns(4)

with col1:
    metric_card(
        "Active Policies",
        str(metrics["active_policies"]),
        f"{metrics['total_policy_versions']} total version artifacts",
        "accent",
    )

with col2:
    metric_card(
        "Executions",
        f"{metrics['successful_executions']} OK",
        f"{metrics['blocked_executions']} blocked",
        "success",
    )

with col3:
    metric_card(
        "zkML Proofs (Audited)",
        str(metrics["proof_success_count"]),
        f"{metrics['verification_success_count']} cryptographically verified",
        "purple",
    )

with col4:
    metric_card(
        "Audit Ledger",
        f"{metrics['audit_events_count']} events",
        f"Chain: {metrics['chain_status']}",
        "warning",
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── 2-column detail panels ───────────────────────────────────
sec_col1, sec_col2 = st.columns(2)

with sec_col1:
    section_title("GOVERNANCE & POLICY HEALTH")
    cyber_card(
        "Policy Compliance Indicators",
        f"""
        <b>Active Policies:</b> {metrics['active_policies']}<br><br>
        <b>Total Policy Versions:</b> {metrics['total_policy_versions']}<br><br>
        <b>Validation Success Rate:</b> {metrics['policy_validation_success_rate']:.1f}%<br><br>
        <b>Policy Rejections:</b> {metrics['policy_rejections']}
        """,
        min_height="170px",
    )

    section_title("ZKML PROOF & VERIFIER HEALTH")
    cyber_card(
        "Proof Verification Compliance",
        f"""
        <b>Proving Completed:</b> {metrics['proof_success_count']}<br><br>
        <b>Proving Failed:</b> {metrics['proof_failure_count']}<br><br>
        <b>Cryptographic Verifications Passed:</b> {metrics['verification_success_count']}<br><br>
        <b>Cryptographic Verifications Failed:</b> {metrics['verification_failure_count']}
        """,
        min_height="170px",
    )

with sec_col2:
    section_title("EXECUTION RUNTIME CONTAINMENT")
    cyber_card(
        "Isolated Process Statistics",
        f"""
        <b>Successful Executions:</b> {metrics['successful_executions']}<br><br>
        <b>Policy-Blocked Actions:</b> {metrics['blocked_executions']}<br><br>
        <b>Execution Containment Failures:</b> {metrics['failed_executions']}<br><br>
        <b>Subprocess Timeouts:</b> {metrics['timed_out_executions']}
        """,
        min_height="170px",
    )

    section_title("AUDIT CHAIN INTEGRITY")
    chain_color = "#10B981" if metrics["chain_status"] == "VALID" else "#F43F5E"
    cyber_card(
        "Append-Only Hash Ledger",
        f"""
        <b>Total Log Entries:</b> {metrics['audit_events_count']}<br><br>
        <b>Hash Status:</b> <strong style="color:{chain_color};">{metrics['chain_status']}</strong><br><br>
        <b>Broken Links:</b> {metrics['broken_links_count']}<br><br>
        <b>Last Entry (IST):</b> {metrics['last_integrity_check'] or '—'}
        """,
        min_height="170px",
    )

st.markdown("<br>", unsafe_allow_html=True)
