from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any

import plotly.express as px
import streamlit as st


FRONTEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = FRONTEND_ROOT.parent

for path in (REPO_ROOT, FRONTEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from components.cards import cyber_card, metric_card, status_badge
from schema.governance_service import get_system_metrics
from utils.audit_parser import (
    get_audit_summary_metrics,
    get_blocked_actions,
    get_recent_threat_activity,
    get_tool_usage_frequency,
    get_verification_statistics,
)
from utils.theme import configure_page, load_global_css, section_title


def _rows_from_counts(counts: Counter[str]) -> list[dict[str, Any]]:
    """Convert a Counter into chart-friendly rows."""

    return [
        {"name": name or "unknown", "count": count}
        for name, count in counts.most_common()
    ]


def _short_hash(value: str | None, length: int = 12) -> str:
    """Return a compact hash preview for tables."""

    if not value:
        return "-"

    return value[:length] + "..."


configure_page("Threat Analytics | NIYAM-AI")
load_global_css()

section_title("THREAT ANALYTICS")
status_badge("REAL GOVERNANCE DATA", "info")

summary = get_audit_summary_metrics()
verification = get_verification_statistics()
system_metrics = get_system_metrics()
blocked_actions = get_blocked_actions()
recent_threats = get_recent_threat_activity(hours=24, limit=15)
tool_usage = get_tool_usage_frequency()

blocked_reasons = Counter(
    row.get("reason", "Unknown")
    for row in blocked_actions
)

threat_tools = Counter(
    row.get("tool_name", "unknown")
    for row in blocked_actions
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    metric_card(
        "Blocked Actions",
        str(summary["blocked_actions"]),
        f"{summary['blocked_rate']}% of audit events",
        "danger",
    )

with col2:
    metric_card(
        "Executed Actions",
        str(summary["executed_actions"]),
        f"{summary['executed_rate']}% execution rate",
        "success",
    )

with col3:
    metric_card(
        "Verified Proofs",
        str(verification["verified"]),
        f"{verification['verification_rate']}% verification rate",
        "normal",
    )

with col4:
    metric_card(
        "Recent Threats",
        str(len(recent_threats)),
        "Blocked in last 24 hours",
        "warning",
    )

st.markdown("<br>", unsafe_allow_html=True)

section_title("BLOCKED ACTION STATISTICS")

chart_col1, chart_col2 = st.columns([1.15, 1])

with chart_col1:
    blocked_tool_rows = _rows_from_counts(threat_tools)

    if blocked_tool_rows:
        fig_blocked_tools = px.bar(
            blocked_tool_rows,
            x="count",
            y="name",
            orientation="h",
            title="Blocked Actions by Tool",
            labels={"count": "Blocked Events", "name": "Tool"},
            color="count",
            color_continuous_scale=["#00D1FF", "#FF3B5C"],
        )
        fig_blocked_tools.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E6F1FF",
            height=360,
        )
        st.plotly_chart(fig_blocked_tools, use_container_width=True)
    else:
        cyber_card(
            "Blocked Actions",
            "No blocked actions found in the audit log.",
            min_height="360px",
        )

with chart_col2:
    reason_rows = _rows_from_counts(blocked_reasons)

    if reason_rows:
        fig_reasons = px.pie(
            reason_rows,
            names="name",
            values="count",
            title="Block Reasons",
            hole=0.45,
            color_discrete_sequence=["#FF3B5C", "#FFC857", "#00D1FF", "#9D4EDD"],
        )
        fig_reasons.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E6F1FF",
            height=360,
        )
        st.plotly_chart(fig_reasons, use_container_width=True)
    else:
        cyber_card(
            "Block Reasons",
            "No blocked reason data is currently available.",
            min_height="360px",
        )

section_title("TOOL USAGE FREQUENCY")

if tool_usage:
    fig_tool_usage = px.bar(
        tool_usage,
        x="tool_name",
        y="count",
        title="Governed Tool Calls",
        labels={"tool_name": "Tool", "count": "Audit Events"},
        color="count",
        color_continuous_scale=["#121A2B", "#00D1FF"],
    )
    fig_tool_usage.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#E6F1FF",
        height=360,
    )
    st.plotly_chart(fig_tool_usage, use_container_width=True)
else:
    cyber_card(
        "Tool Usage",
        "No tool activity is available yet.",
        min_height="220px",
    )

section_title("VERIFICATION SUCCESS")

verify_col1, verify_col2 = st.columns([1, 1])

with verify_col1:
    verification_rows = [
        {"status": "Verified", "count": verification["verified"]},
        {"status": "Failed", "count": verification["failed"]},
        {"status": "Missing", "count": verification["missing"]},
    ]

    fig_verification = px.bar(
        verification_rows,
        x="status",
        y="count",
        title="Proof Verification Coverage",
        labels={"status": "Verification Status", "count": "Records"},
        color="status",
        color_discrete_map={
            "Verified": "#00FF88",
            "Failed": "#FF3B5C",
            "Missing": "#93A4C3",
        },
    )
    fig_verification.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#E6F1FF",
        height=340,
    )
    st.plotly_chart(fig_verification, use_container_width=True)

with verify_col2:
    artifacts = system_metrics.get("artifacts", {})
    proof_artifact = artifacts.get("proof", {})
    witness_artifact = artifacts.get("witness", {})

    cyber_card(
        "Verification Snapshot",
        f"""
        Total audit records: {verification["total_records"]}<br>
        Verified proofs: {verification["verified"]}<br>
        Failed verifications: {verification["failed"]}<br>
        Proof artifact present: {proof_artifact.get("exists", False)}<br>
        Witness artifact present: {witness_artifact.get("exists", False)}
        """,
        min_height="340px",
    )

section_title("RECENT THREAT ACTIVITY")

if recent_threats:
    threat_rows = [
        {
            "timestamp": row.get("timestamp"),
            "tool": row.get("tool_name"),
            "reason": row.get("reason", "-"),
            "session": _short_hash(row.get("session_id")),
            "action_hash": _short_hash(row.get("action_hash")),
        }
        for row in recent_threats
    ]

    st.dataframe(
        threat_rows,
        use_container_width=True,
        hide_index=True,
    )
else:
    cyber_card(
        "Recent Threat Activity",
        "No blocked actions were recorded in the last 24 hours.",
        min_height="180px",
    )
