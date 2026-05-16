from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
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
from schema.governance_service import get_system_metrics, load_audit_logs
from utils.audit_parser import (
    get_audit_summary_metrics,
    get_session_statistics,
    get_verification_statistics,
)
from utils.theme import configure_page, load_global_css, section_title


def _parse_timestamp(value: str | None) -> datetime | None:
    """Parse audit timestamps into UTC datetimes for sorting and display."""

    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def _format_timestamp(value: str | None) -> str:
    """Format audit timestamps for compact table display."""

    parsed = _parse_timestamp(value)
    if parsed is None:
        return "-"

    return parsed.strftime("%Y-%m-%d %H:%M:%S UTC")


def _short_value(value: str | None, length: int = 14) -> str:
    """Return compact identifiers for Streamlit tables."""

    if not value:
        return "-"

    return value[:length] + "..." if len(value) > length else value


def _verification_label(row: dict[str, Any]) -> str:
    """Return a readable proof verification label for one event."""

    if row.get("verification") is True:
        return "VERIFIED"

    if row.get("verification") is False:
        return "FAILED"

    if row.get("proof"):
        return "PROOF_PRESENT"

    return "NOT_AVAILABLE"


def _matches_search(row: dict[str, Any], query: str) -> bool:
    """Search common audit fields without mutating the record."""

    if not query:
        return True

    query = query.lower()
    searchable = [
        row.get("session_id"),
        row.get("intent_hash"),
        row.get("action_hash"),
        row.get("tool_name"),
        row.get("status"),
        row.get("reason"),
        row.get("proof"),
        row.get("timestamp"),
    ]

    return any(query in str(value).lower() for value in searchable if value is not None)


def _table_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert raw audit records into lightweight table rows."""

    return [
        {
            "timestamp": _format_timestamp(row.get("timestamp")),
            "status": row.get("status", "-"),
            "tool": row.get("tool_name", "-"),
            "verification": _verification_label(row),
            "session": _short_value(row.get("session_id")),
            "action_hash": _short_value(row.get("action_hash"), 18),
            "reason": row.get("reason", "-"),
        }
        for row in records
    ]


configure_page("Audit Logs | NIYAM-AI")
load_global_css()

section_title("GOVERNANCE AUDIT LOGS")
status_badge("APPEND-ONLY TRACE", "info")

logs = load_audit_logs()
logs = sorted(
    logs,
    key=lambda row: _parse_timestamp(row.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc),
    reverse=True,
)

summary = get_audit_summary_metrics()
verification = get_verification_statistics()
sessions = get_session_statistics()
system_metrics = get_system_metrics()

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

with metric_col1:
    metric_card(
        "Total Events",
        str(summary["total_actions"]),
        "Audit log records",
        "normal",
    )

with metric_col2:
    metric_card(
        "Executed",
        str(summary["executed_actions"]),
        f"{summary['executed_rate']}% execution rate",
        "success",
    )

with metric_col3:
    metric_card(
        "Blocked",
        str(summary["blocked_actions"]),
        f"{summary['blocked_rate']}% blocked",
        "danger",
    )

with metric_col4:
    metric_card(
        "Sessions",
        str(sessions["unique_sessions"]),
        "Governed sessions",
        "warning",
    )

st.markdown("<br>", unsafe_allow_html=True)

section_title("AUDIT EVENT SEARCH")

if not logs:
    cyber_card(
        "No Audit Events",
        "No governance audit records were found. Run a governed action to populate the audit log.",
        min_height="220px",
    )
    st.stop()

session_options = sorted(
    {row.get("session_id") for row in logs if row.get("session_id")}
)
status_options = sorted(
    {row.get("status") for row in logs if row.get("status")}
)
verification_options = ["VERIFIED", "FAILED", "PROOF_PRESENT", "NOT_AVAILABLE"]

filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([1.4, 1, 1, 1])

with filter_col1:
    search_query = st.text_input(
        "Search audit events",
        placeholder="Search tool, session, hash, status, reason...",
    )

with filter_col2:
    selected_session = st.selectbox(
        "Session",
        ["All Sessions", *session_options],
    )

with filter_col3:
    selected_status = st.selectbox(
        "Status",
        ["All Statuses", *status_options],
    )

with filter_col4:
    selected_verification = st.selectbox(
        "Verification",
        ["All Verification", *verification_options],
    )

filtered_logs = [
    row
    for row in logs
    if _matches_search(row, search_query)
    and (selected_session == "All Sessions" or row.get("session_id") == selected_session)
    and (selected_status == "All Statuses" or row.get("status") == selected_status)
    and (
        selected_verification == "All Verification"
        or _verification_label(row) == selected_verification
    )
]

st.caption(f"Showing {len(filtered_logs)} of {len(logs)} audit events")

if filtered_logs:
    st.dataframe(
        _table_rows(filtered_logs),
        use_container_width=True,
        hide_index=True,
    )
else:
    cyber_card(
        "No Matching Events",
        "No audit records match the current search and filter settings.",
        min_height="180px",
    )

section_title("RECENT EXECUTION TIMELINE")

timeline_rows = [
    {
        "timestamp": _parse_timestamp(row.get("timestamp")),
        "status": row.get("status", "UNKNOWN"),
        "tool": row.get("tool_name", "unknown"),
    }
    for row in filtered_logs
    if _parse_timestamp(row.get("timestamp")) is not None
]

if timeline_rows:
    timeline_rows = sorted(timeline_rows, key=lambda row: row["timestamp"])
    timeline_counts = Counter(
        (
            row["timestamp"].strftime("%Y-%m-%d %H:%M"),
            row["status"],
        )
        for row in timeline_rows
    )
    chart_rows = [
        {"minute": minute, "status": status, "events": count}
        for (minute, status), count in timeline_counts.items()
    ]

    fig_timeline = px.line(
        chart_rows,
        x="minute",
        y="events",
        color="status",
        markers=True,
        title="Governance Events Over Time",
        labels={"minute": "Time", "events": "Events", "status": "Status"},
        color_discrete_map={
            "EXECUTED": "#00FF88",
            "BLOCKED": "#FF3B5C",
            "ERROR": "#FFC857",
            "SAFE": "#00D1FF",
        },
    )
    fig_timeline.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#E6F1FF",
        height=340,
    )
    st.plotly_chart(fig_timeline, use_container_width=True)
else:
    cyber_card(
        "Execution Timeline",
        "No timestamped events are available for the current filter set.",
        min_height="220px",
    )

section_title("PROOF AND VERIFICATION STATUS")

proof_col1, proof_col2 = st.columns([1, 1])

with proof_col1:
    verification_rows = [
        {"status": "Verified", "count": verification["verified"]},
        {"status": "Failed", "count": verification["failed"]},
        {"status": "Missing", "count": verification["missing"]},
    ]

    fig_verification = px.bar(
        verification_rows,
        x="status",
        y="count",
        title="Verification Status by Audit Record",
        labels={"status": "Proof Status", "count": "Records"},
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
        height=320,
    )
    st.plotly_chart(fig_verification, use_container_width=True)

with proof_col2:
    artifacts = system_metrics.get("artifacts", {})
    proof_artifact = artifacts.get("proof", {})
    witness_artifact = artifacts.get("witness", {})

    cyber_card(
        "Proof Artifact State",
        f"""
        Latest proof exists: {proof_artifact.get("exists", False)}<br>
        Proof size: {proof_artifact.get("size_bytes", 0)} bytes<br>
        Proof modified: {proof_artifact.get("modified_at") or "-"}<br>
        Witness exists: {witness_artifact.get("exists", False)}<br>
        Witness modified: {witness_artifact.get("modified_at") or "-"}
        """,
        min_height="320px",
    )

section_title("DETAILED EVENT VIEWER")

if filtered_logs:
    event_labels = [
        f"{index + 1}. {_format_timestamp(row.get('timestamp'))} | {row.get('status', '-')} | {row.get('tool_name', '-')}"
        for index, row in enumerate(filtered_logs)
    ]

    selected_label = st.selectbox(
        "Select event",
        event_labels,
    )
    selected_index = event_labels.index(selected_label)
    selected_event = filtered_logs[selected_index]

    with st.expander("Event Metadata", expanded=True):
        meta_col1, meta_col2, meta_col3 = st.columns(3)

        with meta_col1:
            st.caption("Status")
            status_badge(selected_event.get("status", "UNKNOWN"), "danger" if selected_event.get("status") == "BLOCKED" else "success")

        with meta_col2:
            st.caption("Verification")
            status_badge(_verification_label(selected_event), "success" if selected_event.get("verification") is True else "warning")

        with meta_col3:
            st.caption("Tool")
            st.code(selected_event.get("tool_name", "-"))

        st.caption("Session ID")
        st.code(selected_event.get("session_id", "-"))

        st.caption("Intent Hash")
        st.code(selected_event.get("intent_hash", "-"))

        st.caption("Action Hash")
        st.code(selected_event.get("action_hash", "-"))

        if selected_event.get("proof"):
            st.caption("Proof Artifact")
            st.code(selected_event.get("proof"))

        if selected_event.get("reason"):
            st.caption("Block Reason")
            st.warning(selected_event.get("reason"))

    with st.expander("Raw Audit Record", expanded=False):
        st.json(json.loads(json.dumps(selected_event, default=str)))
else:
    cyber_card(
        "Detailed Event Viewer",
        "Select less restrictive filters to inspect event metadata.",
        min_height="180px",
    )
