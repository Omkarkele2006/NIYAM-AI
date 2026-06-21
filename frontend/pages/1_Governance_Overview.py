import sys
from pathlib import Path
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from schema.governance_service import get_dashboard_overview_metrics
from utils.theme import configure_page, load_global_css, section_title, cyber_header
from components.cards import metric_card, cyber_card, status_badge

configure_page("Governance Overview | NIYAM-AI")
load_global_css()

cyber_header(
    "GOVERNANCE CONTROL CENTER",
    "Unified security visibility, policy verification, and audit integrity metrics"
)

status_badge("SYSTEM MONITORING ACTIVE", "success")

st.markdown("<br>", unsafe_allow_html=True)

# Fetch metrics
metrics = get_dashboard_overview_metrics()

# 1. Row of 4 Primary Metric Cards
st.subheader("System Health Overview")
col1, col2, col3, col4 = st.columns(4)

with col1:
    metric_card(
        "Active Policies",
        str(metrics["active_policies"]),
        f"Versions: {metrics['total_policy_versions']} total",
        "success"
    )

with col2:
    metric_card(
        "Execution Rate",
        f"{metrics['successful_executions']} OK",
        f"{metrics['blocked_executions']} BLOCKED",
        "normal"
    )

with col3:
    metric_card(
        "zkML Pipelines",
        f"{metrics['proof_success_count']} Proofs",
        f"{metrics['verification_success_count']} Verified",
        "warning"
    )

with col4:
    metric_card(
        "Audit Ledger",
        str(metrics["audit_events_count"]) + " Events",
        f"Chain: {metrics['chain_status']}",
        "danger"
    )

st.markdown("<br>", unsafe_allow_html=True)

# 2. Detailed health columns
sec_col1, sec_col2 = st.columns(2)

with sec_col1:
    section_title("GOVERNANCE & POLICY HEALTH")
    cyber_card(
        "Policy Compliance Indicators",
        f"""
        • <b>Active Policies Count:</b> {metrics['active_policies']}<br><br>
        • <b>Total Policy Version Artifacts:</b> {metrics['total_policy_versions']}<br><br>
        • <b>Policy Validation Success Rate:</b> {metrics['policy_validation_success_rate']:.1f}%<br><br>
        • <b>Governance Policy Rejections:</b> {metrics['policy_rejections']}<br>
        """,
        min_height="180px"
    )

    section_title("ZKML PROOF & VERIFIER HEALTH")
    cyber_card(
        "Proof Verification Compliance",
        f"""
        • <b>Proving Completed:</b> {metrics['proof_success_count']}<br><br>
        • <b>Proving Failed:</b> {metrics['proof_failure_count']}<br><br>
        • <b>Cryptographic Verifications Passed:</b> {metrics['verification_success_count']}<br><br>
        • <b>Cryptographic Verifications Failed:</b> {metrics['verification_failure_count']}<br>
        """,
        min_height="180px"
    )

with sec_col2:
    section_title("EXECUTION RUNTIME CONTAINMENT")
    cyber_card(
        "Isolated Process Statistics",
        f"""
        • <b>Successful Executions:</b> {metrics['successful_executions']}<br><br>
        • <b>Policy Blocked Actions:</b> {metrics['blocked_executions']}<br><br>
        • <b>Execution Containment Failures:</b> {metrics['failed_executions']}<br><br>
        • <b>Subprocess Timeouts / Terminated:</b> {metrics['timed_out_executions']}<br>
        """,
        min_height="180px"
    )

    section_title("AUDIT CHAIN INTEGRITY")
    chain_color = "#00FF88" if metrics["chain_status"] == "VALID" else "#FF3B5C"
    cyber_card(
        "Append-Only Hash Ledger",
        f"""
        • <b>Total Log Entries Recorded:</b> {metrics['audit_events_count']}<br><br>
        • <b>Cryptographic Hash Status:</b> <strong style='color:{chain_color};'>{metrics['chain_status']}</strong><br><br>
        • <b>Detected Broken Links:</b> {metrics['broken_links_count']}<br><br>
        • <b>Last Log Entry Time (IST):</b> {metrics['last_integrity_check'] or '-'}<br>
        """,
        min_height="180px"
    )

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    """
    <div style="text-align:center; color:#93A4C3; font-size:0.9rem;">
        NIYAM-AI • Governance Dashboard Overview
    </div>
    """,
    unsafe_allow_html=True
)
