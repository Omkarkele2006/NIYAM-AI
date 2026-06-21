from __future__ import annotations

import sys
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
from schema.governance_service import get_system_metrics, get_dashboard_overview_metrics
from utils.audit_parser import (
    get_audit_summary_metrics,
    get_blocked_actions,
    get_executed_actions,
    get_latest_audit_logs,
    get_recent_threat_activity,
    get_verification_statistics,
)
from utils.proof_reader import (
    get_latest_proof_metadata,
    get_verification_key_metadata,
    get_witness_artifact,
)
from utils.theme import configure_page, load_global_css, section_title
from utils.time_utils import format_timestamp_short, parse_utc_timestamp


def _format_timestamp(value: str | None) -> str:
    """Format timestamps for realtime event cards in IST."""
    return format_timestamp_short(value)


def _short_value(value: str | None, length: int = 12) -> str:
    """Return a compact identifier preview."""

    if not value:
        return "-"

    return value[:length] + "..." if len(value) > length else value


def _status_color(status: str | None) -> str:
    """Map event status to a cyber color."""

    if status == "EXECUTED":
        return "#00FF88"

    if status == "BLOCKED":
        return "#FF3B5C"

    if status == "ERROR":
        return "#FFC857"

    return "#00D1FF"


def _event_card(row: dict[str, Any]) -> None:
    """Render a compact realtime governance event card."""

    status = row.get("status", "UNKNOWN")
    color = _status_color(status)
    reason = row.get("reason") or "Governance checks completed"

    st.markdown(
        f"""
<div style="background: rgba(18,26,43,0.78); border-left: 4px solid {color}; border-radius: 12px; padding: 0.95rem 1.1rem; margin-bottom: 0.75rem; border-top: 1px solid rgba(255,255,255,0.08); border-right: 1px solid rgba(255,255,255,0.08); border-bottom: 1px solid rgba(255,255,255,0.08);">
<div style="display:flex; justify-content:space-between; gap:1rem; align-items:center;">
<strong style="color:{color};">{status}</strong>
<span style="color:#93A4C3; font-size:0.82rem;">{_format_timestamp(row.get("timestamp"))}</span>
</div>
<div style="color:#E6F1FF; margin-top:0.45rem;">Tool: <b>{row.get("tool_name", "-")}</b></div>
<div style="color:#93A4C3; font-size:0.85rem; margin-top:0.35rem;">ActionHash: {_short_value(row.get("action_hash"), 18)}</div>
<div style="color:#93A4C3; font-size:0.85rem; margin-top:0.35rem;">{reason}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def _pipeline_stage(label: str, state: str, status: str = "active", index: int = 1) -> str:
    """Return one polished HTML stage for the execution pipeline."""

    color_map = {
        "active": "#00D1FF",
        "success": "#00FF88",
        "warning": "#FFC857",
        "danger": "#FF3B5C",
        "idle": "#93A4C3",
    }
    color = color_map.get(status, "#00D1FF")

    return f"""
<div class="gov-pipeline-stage gov-stage-{status}" style="--stage-color:{color};">
<div class="gov-stage-index">{index:02d}</div>
<div class="gov-stage-indicator"></div>
<div class="gov-stage-label">{label}</div>
<div class="gov-stage-state">{state}</div>
</div>
"""


def _render_governance_pipeline(
    *,
    latest_status: str | None,
    proof_exists: bool,
    witness_exists: bool,
    verified_count: int,
    total_actions: int,
) -> None:
    """Render the realtime enterprise governance execution flow."""

    execution_state = (
        "executed"
        if latest_status == "EXECUTED"
        else "blocked"
        if latest_status == "BLOCKED"
        else "standing by"
    )
    proof_state = "proof ready" if proof_exists else "awaiting proof"
    verification_state = f"{verified_count} verified" if verified_count else "awaiting verification"
    audit_state = "logging active" if total_actions else "awaiting events"

    tool_gate_status = "danger" if latest_status == "BLOCKED" else "success" if latest_status else "active"
    proof_status = "success" if proof_exists and witness_exists else "warning"
    verification_status = "success" if verified_count else "warning"
    execution_status = (
        "success"
        if latest_status == "EXECUTED"
        else "danger"
        if latest_status == "BLOCKED"
        else "active"
    )
    audit_status = "success" if total_actions else "warning"

    stages = [
        _pipeline_stage("Prompt", "captured", "active", 1),
        _pipeline_stage("Intent Validation", "contract sealed", "success", 2),
        _pipeline_stage("Tool Gate", "authority checked", tool_gate_status, 3),
        _pipeline_stage("zkML Proof", proof_state, proof_status, 4),
        _pipeline_stage("Verification", verification_state, verification_status, 5),
        _pipeline_stage("Execution", execution_state, execution_status, 6),
        _pipeline_stage("Audit Logging", audit_state, audit_status, 7),
    ]

    pipeline_html = f"""
<style>
.gov-pipeline-shell {{
    position: relative;
    overflow: hidden;
    padding: 1.25rem;
    margin-bottom: 1.45rem;
    border: 1px solid rgba(0,209,255,0.18);
    border-radius: 18px;
    background:
        linear-gradient(180deg, rgba(18,26,43,0.84), rgba(8,12,24,0.92)),
        radial-gradient(circle at 18% 0%, rgba(0,209,255,0.12), transparent 34%),
        radial-gradient(circle at 88% 20%, rgba(157,78,221,0.10), transparent 32%);
    box-shadow:
        0 10px 36px rgba(0,0,0,0.24),
        inset 0 1px 0 rgba(255,255,255,0.04);
}}
.gov-pipeline-shell::before {{
    content: "";
    position: absolute;
    left: 1.45rem;
    right: 1.45rem;
    top: 50%;
    height: 2px;
    background:
        linear-gradient(
            90deg,
            rgba(0,209,255,0.15),
            rgba(0,209,255,0.72),
            rgba(157,78,221,0.60),
            rgba(0,255,136,0.44)
        );
    box-shadow: 0 0 16px rgba(0,209,255,0.20);
    transform: translateY(-50%);
}}
.gov-pipeline-flow {{
    position: relative;
    z-index: 1;
    display: grid;
    grid-template-columns: repeat(7, minmax(132px, 1fr));
    gap: 0.75rem;
    align-items: stretch;
}}
.gov-pipeline-stage {{
    position: relative;
    min-height: 142px;
    padding: 1rem 0.85rem 0.95rem;
    text-align: center;
    border: 1px solid color-mix(in srgb, var(--stage-color) 62%, transparent);
    border-radius: 15px;
    background:
        linear-gradient(180deg, rgba(18,26,43,0.95), rgba(9,14,28,0.95));
    box-shadow:
        0 0 18px color-mix(in srgb, var(--stage-color) 14%, transparent),
        inset 0 1px 0 rgba(255,255,255,0.04);
    transition: transform 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease;
}}
.gov-pipeline-stage:hover {{
    transform: translateY(-2px);
    border-color: var(--stage-color);
    box-shadow:
        0 0 24px color-mix(in srgb, var(--stage-color) 22%, transparent),
        0 8px 28px rgba(0,0,0,0.22);
}}
.gov-stage-index {{
    position: absolute;
    left: 0.75rem;
    top: 0.65rem;
    color: rgba(230,241,255,0.34);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
}}
.gov-stage-indicator {{
    width: 18px;
    height: 18px;
    margin: 1.15rem auto 0.75rem;
    border-radius: 50%;
    background: var(--stage-color);
    box-shadow:
        0 0 0 5px color-mix(in srgb, var(--stage-color) 12%, transparent),
        0 0 20px color-mix(in srgb, var(--stage-color) 34%, transparent);
    animation: govPulse 2.8s ease-in-out infinite;
}}
.gov-stage-success .gov-stage-indicator,
.gov-stage-danger .gov-stage-indicator {{
    animation-duration: 3.8s;
}}
.gov-stage-label {{
    color: #E6F1FF;
    font-family: 'Orbitron', sans-serif;
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    line-height: 1.35;
}}
.gov-stage-state {{
    color: #93A4C3;
    margin-top: 0.55rem;
    font-size: 0.76rem;
    line-height: 1.45;
}}
.gov-pipeline-meta {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.8rem;
    margin-top: 1rem;
    color: #93A4C3;
    font-size: 0.82rem;
}}
.gov-pipeline-meta span {{
    border: 1px solid rgba(0,209,255,0.14);
    border-radius: 999px;
    padding: 0.35rem 0.7rem;
    background: rgba(5,8,20,0.42);
}}
@keyframes govPulse {{
    0%, 100% {{
        transform: scale(1);
        opacity: 0.88;
    }}
    50% {{
        transform: scale(1.08);
        opacity: 1;
    }}
}}
@media (max-width: 1200px) {{
    .gov-pipeline-shell::before {{
        display: none;
    }}
    .gov-pipeline-flow {{
        grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    }}
}}
</style>
<div class="gov-pipeline-shell">
<div class="gov-pipeline-flow">
{''.join(stages)}
</div>
<div class="gov-pipeline-meta">
<span>Latest status: {latest_status or "IDLE"}</span>
<span>Proof artifact: {"online" if proof_exists else "missing"}</span>
<span>Witness artifact: {"online" if witness_exists else "missing"}</span>
<span>Audit events: {total_actions}</span>
</div>
</div>
"""
    st.markdown(pipeline_html, unsafe_allow_html=True)


configure_page("Live Monitor | NIYAM-AI")
load_global_css()

section_title("LIVE GOVERNANCE MONITOR")
status_badge("OPERATIONS ACTIVE", "success")

refresh_col1, refresh_col2, refresh_col3 = st.columns([1, 1, 4])

with refresh_col1:
    auto_refresh = st.toggle("Auto-refresh", value=False)

with refresh_col2:
    refresh_seconds = st.number_input(
        "Seconds",
        min_value=5,
        max_value=120,
        value=15,
        step=5,
    )

with refresh_col3:
    st.caption("Last rendered at 📡")

if auto_refresh:
    st.markdown(
        f"<meta http-equiv='refresh' content='{int(refresh_seconds)}'>",
        unsafe_allow_html=True,
    )

summary = get_audit_summary_metrics()
system_metrics = get_system_metrics()
verification = get_verification_statistics()
latest_events = get_latest_audit_logs(limit=8)
blocked_actions = get_blocked_actions(limit=5)
executed_actions = get_executed_actions(limit=5)
recent_threats = get_recent_threat_activity(hours=24, limit=5)
proof = get_latest_proof_metadata()
witness = get_witness_artifact()
verification_key = get_verification_key_metadata()

st.markdown("<br>", unsafe_allow_html=True)

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

with metric_col1:
    metric_card(
        "Total Events",
        str(summary["total_actions"]),
        "Governance audit stream",
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
        "Verified Proofs",
        str(verification["verified"]),
        f"{verification['verification_rate']}% coverage",
        "warning",
    )

section_title("GOVERNANCE EXECUTION PIPELINE")

latest_status = summary.get("latest_status")
_render_governance_pipeline(
    latest_status=latest_status,
    proof_exists=proof["exists"],
    witness_exists=witness["exists"],
    verified_count=verification["verified"],
    total_actions=summary["total_actions"],
)

section_title("OPERATIONS STREAM")

stream_col, alert_col = st.columns([1.35, 1])

with stream_col:
    cyber_card(
        "Live Governance Event Stream",
        "Latest governed actions from the append-only audit log.",
        min_height="90px",
    )

    if latest_events:
        for event in latest_events:
            _event_card(event)
    else:
        cyber_card(
            "No Events",
            "No governance events have been recorded yet.",
            min_height="180px",
        )

with alert_col:
    cyber_card(
        "Blocked Action Alerts",
        f"{len(recent_threats)} blocked actions detected in the recent threat window.",
        min_height="90px",
    )

    if blocked_actions:
        for event in blocked_actions:
            _event_card(event)
    else:
        cyber_card(
            "No Blocked Actions",
            "No blocked actions are currently present in the audit stream.",
            min_height="180px",
        )

section_title("RECENT EXECUTIONS AND PROOF ACTIVITY")

exec_col, proof_col = st.columns([1, 1])

with exec_col:
    if executed_actions:
        execution_rows = [
            {
                "time": _format_timestamp(row.get("timestamp")),
                "tool": row.get("tool_name", "-"),
                "session": _short_value(row.get("session_id")),
                "action_hash": _short_value(row.get("action_hash"), 18),
            }
            for row in executed_actions
        ]
        st.dataframe(execution_rows, use_container_width=True, hide_index=True)
    else:
        cyber_card(
            "Recent Executions",
            "No recent executed actions are available.",
            min_height="220px",
        )

with proof_col:
    proof_events = [
        {"status": "Verified", "count": verification["verified"]},
        {"status": "Failed", "count": verification["failed"]},
        {"status": "Missing", "count": verification["missing"]},
    ]

    fig_proof = px.bar(
        proof_events,
        x="status",
        y="count",
        title="Proof Verification Activity",
        labels={"status": "Proof State", "count": "Audit Records"},
        color="status",
        color_discrete_map={
            "Verified": "#00FF88",
            "Failed": "#FF3B5C",
            "Missing": "#93A4C3",
        },
    )
    fig_proof.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#E6F1FF",
        height=300,
    )
    st.plotly_chart(fig_proof, use_container_width=True)

section_title("EXECUTION RUNTIME CONTAINMENT (SANDBOX PROCESS ISOLATION)")

fsm_col1, fsm_col2, fsm_col3, fsm_col4 = st.columns(4)
overview_metrics = get_dashboard_overview_metrics()

with fsm_col1:
    metric_card(
        "Completed Execs",
        str(overview_metrics["successful_executions"]),
        "Processed successfully",
        "success"
    )
with fsm_col2:
    metric_card(
        "Blocked Execs",
        str(overview_metrics["blocked_executions"]),
        "Policy constraints enforced",
        "danger"
    )
with fsm_col3:
    metric_card(
        "Containment Fails",
        str(overview_metrics["failed_executions"]),
        "Runtime error blocks",
        "warning"
    )
with fsm_col4:
    metric_card(
        "Subprocess Timeouts",
        str(overview_metrics["timed_out_executions"]),
        "Killed by timeout watchdog",
        "danger"
    )

st.markdown("<br>", unsafe_allow_html=True)

section_title("SYSTEM HEALTH INDICATORS")

health_col1, health_col2, health_col3 = st.columns(3)

with health_col1:
    cyber_card(
        "Proof Pipeline Activity",
        f"""
        Proof artifact: {proof["exists"]}<br>
        Witness artifact: {witness["exists"]}<br>
        Verification key: {verification_key["exists"]}<br>
        Latest proof modified: {proof.get("modified_at") or "-"}
        """,
        min_height="240px",
    )

with health_col2:
    artifacts = system_metrics.get("artifacts", {})
    circuit = artifacts.get("circuit", {})

    cyber_card(
        "Security Artifacts",
        f"""
        Circuit present: {circuit.get("exists", False)}<br>
        VK size: {verification_key.get("size_bytes", 0)} bytes<br>
        Proof size: {proof.get("size_bytes", 0)} bytes<br>
        Witness size: {witness.get("size_bytes", 0)} bytes
        """,
        min_height="240px",
    )

with health_col3:
    cyber_card(
        "Recent Proof Generation Events",
        f"""
        Verified proof records: {verification["verified"]}<br>
        Failed proof records: {verification["failed"]}<br>
        Missing proof records: {verification["missing"]}<br>
        Latest governed tool: {summary.get("latest_tool") or "-"}
        """,
        min_height="240px",
    )
