"""
Orchestration Governance Monitor — NIYAM-AI (read-only observability).

Governance boundaries enforced in this file:
  - No imports from schema.orchestration
  - No execution triggers or interactive runtime controls
  - All data sourced through orchestration_parser.py and load_audit_logs()
  - Payload and feature fields are never rendered
  - All hash / session identifiers are truncated before display
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any

import plotly.express as px
import streamlit as st

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = FRONTEND_ROOT.parent

for _path in (REPO_ROOT, FRONTEND_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from components.cards import cyber_card, metric_card, status_badge
from schema.governance_service import load_audit_logs
from utils.chart_theme import (
    apply_cyber_theme,
    create_glow_bar_chart,
    create_governance_pie_chart,
    create_timeline_chart,
    GOVERNANCE_STATUS_COLORS,
)
from utils.orchestration_parser import (
    get_blocked_proposal_analytics,
    get_intent_hash_groups,
    get_orchestration_overview,
    get_orchestration_timeline,
    get_proposal_status_distribution,
    get_session_list,
    get_session_proposals,
)
from utils.theme import configure_page, load_global_css, section_title, page_header
from utils.time_utils import format_timestamp_short, format_timestamp_table


# ---------------------------------------------------------------------------
# Local display helpers — mirrors pattern from 4_Audit_Logs.py and Live Monitor
# ---------------------------------------------------------------------------

def _short_id(value: str | None, length: int = 14) -> str:
    """Truncate a session ID or hash for compact UI display."""
    if not value:
        return "-"
    return value[:length] + "..." if len(value) > length else value


def _format_ts(value: str | None) -> str:
    """Format an ISO timestamp to HH:MM AM/PM IST for event cards."""
    return format_timestamp_short(value)


def _format_ts_full(value: str | None) -> str:
    """Format an ISO timestamp to YYYY-MM-DD HH:MM IST for tables."""
    return format_timestamp_table(value)


def _status_color(status: str | None) -> str:
    """Map a governance status string to an enterprise color."""
    mapping = {
        "EXECUTED": "#10B981",
        "BLOCKED":  "#F43F5E",
        "ERROR":    "#F59E0B",
    }
    return mapping.get(str(status).upper() if status else "", "#22D3EE")


def _verification_label(row: dict[str, Any]) -> str:
    """Return a readable proof verification label for one audit record."""
    v = row.get("verification")
    if v is True:
        return "VERIFIED"
    if v is False:
        return "FAILED"
    if row.get("proof"):
        return "PROOF_PRESENT"
    return "NOT_AVAILABLE"


# ---------------------------------------------------------------------------
# Proposal event card — mirrors _event_card() in 1_Live_Monitor.py exactly
# ---------------------------------------------------------------------------

def _proposal_card(row: dict[str, Any]) -> None:
    """Render one proposal lifecycle event card."""
    status = row.get("status", "UNKNOWN")
    color  = _status_color(status)
    reason = row.get("reason", "-")
    if reason == "-":
        reason = "Governance pipeline completed"

    st.markdown(
        f"""
<div style="background:var(--bg-card);border-left:3px solid {color};border:1px solid var(--border);border-left:3px solid {color};border-radius:10px;padding:0.85rem 1rem;margin-bottom:0.6rem;">
  <div style="display:flex;justify-content:space-between;gap:1rem;align-items:center;">
    <strong style="color:{color};font-size:0.85rem;">{status}</strong>
    <span style="color:#6B7280;font-size:0.78rem;">{_format_ts(row.get('timestamp'))}</span>
  </div>
  <div style="color:#E6E9EF;margin-top:0.4rem;font-size:0.88rem;">
    Tool: <b>{row.get('tool', '-')}</b>
  </div>
  <div style="color:#9AA3B2;font-size:0.8rem;margin-top:0.3rem;">
    ActionHash: {row.get('action_hash', '-')}
  </div>
  <div style="color:#9AA3B2;font-size:0.8rem;margin-top:0.3rem;">
    Proof: {row.get('verification', '-')} &nbsp;|&nbsp; {reason}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Orchestration pipeline — adapted from _render_governance_pipeline() in
# 1_Live_Monitor.py.  CSS classes are identical; grid is 6-column.
# ---------------------------------------------------------------------------

def _pipeline_stage(label: str, state: str, status: str = "active", index: int = 1) -> str:
    color_map = {
        "active":  "#22D3EE",
        "success": "#10B981",
        "warning": "#F59E0B",
        "danger":  "#F43F5E",
        "idle":    "#4B5563",
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


def _render_orchestration_pipeline(
    *,
    latest_status: str | None,
    total_proposals: int,
    unique_sessions: int,
    verified_count: int,
    blocked_count: int,
) -> None:
    """Render the 6-stage orchestration governance pipeline visualization."""

    has_sessions  = unique_sessions > 0
    has_proposals = total_proposals > 0

    planner_st     = "success" if has_sessions  else "idle"
    proposal_st    = "success" if has_proposals else "idle"
    interceptor_st = "success" if has_proposals else "idle"
    proof_st       = "success" if verified_count > 0 else ("warning" if has_proposals else "idle")
    outcome_st     = (
        "success" if latest_status == "EXECUTED"
        else "danger" if latest_status == "BLOCKED"
        else "active"
    )
    outcome_state  = (
        "executed" if latest_status == "EXECUTED"
        else "blocked" if latest_status == "BLOCKED"
        else "standing by"
    )

    stages = [
        _pipeline_stage("Prompt",          "captured",               "active",      1),
        _pipeline_stage("SecurePlanner",   f"{unique_sessions} sess", planner_st,   2),
        _pipeline_stage("Proposal",        f"{total_proposals} props",proposal_st,  3),
        _pipeline_stage("Interceptor",     "proof pipeline",          interceptor_st,4),
        _pipeline_stage("Proof & Verify",  f"{verified_count} verif", proof_st,     5),
        _pipeline_stage("Gov. Outcome",    outcome_state,             outcome_st,   6),
    ]

    pipeline_html = f"""
<style>
.gov-pipeline-shell{{position:relative;overflow:hidden;padding:1.25rem;
  margin-bottom:1.45rem;border:1px solid rgba(0,209,255,0.18);border-radius:18px;
  background:linear-gradient(180deg,rgba(18,26,43,0.84),rgba(8,12,24,0.92)),
    radial-gradient(circle at 18% 0%,rgba(0,209,255,0.12),transparent 34%),
    radial-gradient(circle at 88% 20%,rgba(157,78,221,0.10),transparent 32%);
  box-shadow:0 10px 36px rgba(0,0,0,0.24),inset 0 1px 0 rgba(255,255,255,0.04);}}
.gov-pipeline-shell::before{{content:"";position:absolute;left:1.45rem;right:1.45rem;
  top:50%;height:2px;background:linear-gradient(90deg,rgba(0,209,255,0.15),
  rgba(0,209,255,0.72),rgba(157,78,221,0.60),rgba(0,255,136,0.44));
  box-shadow:0 0 16px rgba(0,209,255,0.20);transform:translateY(-50%);}}
.gov-pipeline-flow{{position:relative;z-index:1;display:grid;
  grid-template-columns:repeat(6,minmax(130px,1fr));gap:0.75rem;align-items:stretch;}}
.gov-pipeline-stage{{position:relative;min-height:142px;padding:1rem 0.85rem 0.95rem;
  text-align:center;border:1px solid color-mix(in srgb,var(--stage-color) 62%,transparent);
  border-radius:15px;background:linear-gradient(180deg,rgba(18,26,43,0.95),rgba(9,14,28,0.95));
  box-shadow:0 0 18px color-mix(in srgb,var(--stage-color) 14%,transparent),
    inset 0 1px 0 rgba(255,255,255,0.04);
  transition:transform 0.22s ease,border-color 0.22s ease,box-shadow 0.22s ease;}}
.gov-pipeline-stage:hover{{transform:translateY(-2px);border-color:var(--stage-color);
  box-shadow:0 0 24px color-mix(in srgb,var(--stage-color) 22%,transparent),
    0 8px 28px rgba(0,0,0,0.22);}}
.gov-stage-index{{position:absolute;left:0.75rem;top:0.65rem;color:rgba(230,241,255,0.34);
  font-size:0.72rem;font-weight:700;letter-spacing:0.08em;}}
.gov-stage-indicator{{width:18px;height:18px;margin:1.15rem auto 0.75rem;border-radius:50%;
  background:var(--stage-color);
  box-shadow:0 0 0 5px color-mix(in srgb,var(--stage-color) 12%,transparent),
    0 0 20px color-mix(in srgb,var(--stage-color) 34%,transparent);
  animation:govPulse 2.8s ease-in-out infinite;}}
.gov-stage-success .gov-stage-indicator,.gov-stage-danger .gov-stage-indicator{{animation-duration:3.8s;}}
.gov-stage-label{{color:#E6F1FF;font-family:'Orbitron',sans-serif;font-size:0.82rem;
  font-weight:700;letter-spacing:0.04em;line-height:1.35;}}
.gov-stage-state{{color:#93A4C3;margin-top:0.55rem;font-size:0.76rem;line-height:1.45;}}
.gov-pipeline-meta{{display:flex;flex-wrap:wrap;gap:0.8rem;margin-top:1rem;
  color:#93A4C3;font-size:0.82rem;}}
.gov-pipeline-meta span{{border:1px solid rgba(0,209,255,0.14);border-radius:999px;
  padding:0.35rem 0.7rem;background:rgba(5,8,20,0.42);}}
@keyframes govPulse{{0%,100%{{transform:scale(1);opacity:0.88;}}50%{{transform:scale(1.08);opacity:1;}}}}
@media(max-width:1200px){{.gov-pipeline-shell::before{{display:none;}}
  .gov-pipeline-flow{{grid-template-columns:repeat(auto-fit,minmax(170px,1fr));}}}}
</style>
<div class="gov-pipeline-shell">
  <div class="gov-pipeline-flow">{''.join(stages)}</div>
  <div class="gov-pipeline-meta">
    <span>Sessions: {unique_sessions}</span>
    <span>Proposals: {total_proposals}</span>
    <span>Blocked: {blocked_count}</span>
    <span>Latest outcome: {latest_status or "IDLE"}</span>
  </div>
</div>
"""
    st.markdown(pipeline_html, unsafe_allow_html=True)


# ===========================================================================
# PAGE
# ===========================================================================

configure_page("Orchestration Monitor | NIYAM-AI")
load_global_css()

# ---------------------------------------------------------------------------
# Load all data up-front — each parser call reads from audit_log.jsonl only
# ---------------------------------------------------------------------------

overview     = get_orchestration_overview()
distribution = get_proposal_status_distribution()
analytics    = get_blocked_proposal_analytics()
timeline_data = get_orchestration_timeline()
session_summary = get_session_list()
intent_groups   = get_intent_hash_groups()
all_logs = load_audit_logs()          # used for lineage table + session_id map

# Build full-session-id list for selectbox (full IDs needed for parser calls)
_full_session_ids: list[str] = sorted(
    {row.get("session_id") for row in all_logs if row.get("session_id")},
    reverse=True,
)


# ---------------------------------------------------------------------------
# SECTION 1: Header
# ---------------------------------------------------------------------------

page_header(
    "Orchestration Monitor",
    "Governance proposal lifecycle, session analytics, and orchestration chain observability",
    badge_label="READ-ONLY",
    badge_kind="muted",
)


# ---------------------------------------------------------------------------
# SECTION 2: Overview metrics
# ---------------------------------------------------------------------------

m1, m2, m3, m4 = st.columns(4)

with m1:
    metric_card(
        "Sessions",
        str(overview["unique_sessions"]),
        "Distinct orchestration sessions",
        "normal",
    )
with m2:
    metric_card(
        "Total Proposals",
        str(overview["total_proposals"]),
        "Governed action proposals",
        "normal",
    )
with m3:
    metric_card(
        "Executed",
        str(overview["executed_proposals"]),
        f"{overview['executed_rate']}% execution rate",
        "success",
    )
with m4:
    metric_card(
        "Blocked",
        str(overview["blocked_proposals"]),
        f"{overview['blocked_rate']}% blocked",
        "danger",
    )

st.markdown("<br>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# SECTION 3: Lifecycle pipeline
# ---------------------------------------------------------------------------

section_title("ORCHESTRATION GOVERNANCE PIPELINE")

_verified_count = sum(
    1 for row in all_logs if row.get("verification") is True
)

_render_orchestration_pipeline(
    latest_status=overview.get("latest_status"),
    total_proposals=overview["total_proposals"],
    unique_sessions=overview["unique_sessions"],
    verified_count=_verified_count,
    blocked_count=overview["blocked_proposals"],
)


# ---------------------------------------------------------------------------
# SECTION 4: Session Explorer
# ---------------------------------------------------------------------------

section_title("SESSION EXPLORER")

sess_col, outcome_col = st.columns([1.35, 1])

with sess_col:
    if _full_session_ids:
        selected_session = st.selectbox(
            "Select orchestration session",
            options=_full_session_ids,
            format_func=_short_id,
        )

        session_proposals = get_session_proposals(selected_session)

        cyber_card(
            "Proposal Lifecycle Stream",
            f"Showing {len(session_proposals)} proposal(s) for session "
            f"{_short_id(selected_session)}.",
            min_height="60px",
        )

        if session_proposals:
            for prop in session_proposals:
                _proposal_card(prop)
        else:
            cyber_card(
                "No Proposals",
                "No proposal records found for this session.",
                min_height="120px",
            )
    else:
        cyber_card(
            "No Sessions Recorded",
            "No orchestration sessions are present in the audit log yet.",
            min_height="280px",
        )
        session_proposals = []
        selected_session = None

with outcome_col:
    if session_proposals:
        _sess_counts = Counter(p.get("status", "UNKNOWN") for p in session_proposals)
        _sess_dist = [
            {"status": s, "count": c}
            for s, c in _sess_counts.items()
            if c > 0
        ]
        fig_sess = create_governance_pie_chart(
            _sess_dist,
            names="status",
            values="count",
            title="Session Outcome Distribution",
            height=300,
        )
        st.plotly_chart(fig_sess, use_container_width=True)

        _exec_s  = _sess_counts.get("EXECUTED", 0)
        _block_s = _sess_counts.get("BLOCKED",  0)
        _total_s = len(session_proposals)
        _rate_s  = round((_exec_s / _total_s) * 100, 1) if _total_s else 0.0

        cyber_card(
            "Session Summary",
            f"""
            Session: {_short_id(selected_session)}<br>
            Total proposals: {_total_s}<br>
            Executed: {_exec_s}<br>
            Blocked: {_block_s}<br>
            Governance rate: {_rate_s}%
            """,
            min_height="220px",
        )
    else:
        cyber_card(
            "Session Outcome",
            "Select a session with recorded proposals to view its outcome breakdown.",
            min_height="380px",
        )


# ---------------------------------------------------------------------------
# SECTION 5: Proposal Status Analytics
# ---------------------------------------------------------------------------

section_title("PROPOSAL STATUS ANALYTICS")

stat_col1, stat_col2 = st.columns([1.15, 1])

with stat_col1:
    _tool_counts = Counter(
        row.get("tool_name", "unknown") for row in all_logs
    )
    _tool_rows = [
        {"tool_name": t or "unknown", "count": c}
        for t, c in _tool_counts.most_common()
    ]
    if _tool_rows:
        fig_tools = create_glow_bar_chart(
            _tool_rows,
            x="tool_name",
            y="count",
            title="Proposals by Governed Tool",
            labels={"tool_name": "Tool", "count": "Proposals"},
            height=360,
        )
        st.plotly_chart(fig_tools, use_container_width=True)
    else:
        cyber_card("Tool Activity", "No tool proposals recorded yet.", min_height="360px")

with stat_col2:
    if distribution:
        fig_dist = create_governance_pie_chart(
            distribution,
            names="status",
            values="count",
            title="Proposal Outcome Distribution",
            height=360,
        )
        st.plotly_chart(fig_dist, use_container_width=True)
    else:
        cyber_card("Outcome Distribution", "No proposals recorded yet.", min_height="360px")


# ---------------------------------------------------------------------------
# SECTION 6: Blocked Proposal Analytics
# ---------------------------------------------------------------------------

section_title("BLOCKED PROPOSAL ANALYTICS")

block_col1, block_col2 = st.columns([1.15, 1])

with block_col1:
    reason_data = analytics.get("reason_distribution", [])
    if reason_data:
        fig_reasons = create_glow_bar_chart(
            reason_data,
            x="count",
            y="reason",
            title="Block Reasons",
            orientation="h",
            labels={"count": "Blocked Events", "reason": "Reason"},
            height=360,
        )
        st.plotly_chart(fig_reasons, use_container_width=True)
    else:
        cyber_card(
            "Block Reasons",
            "No blocked proposals are currently present in the audit log.",
            min_height="360px",
        )

with block_col2:
    cyber_card(
        "Governance Enforcement Summary",
        f"""
        Total blocked proposals: {analytics['total_blocked']}<br><br>
        Block rate: {analytics['block_rate']}% of all proposals<br><br>
        Most blocked tool: {analytics['most_blocked_tool'] or '-'}<br><br>
        Most common reason: {analytics['most_common_reason'] or '-'}<br><br>
        Latest block: {analytics['latest_block_ts'] or '-'}
        """,
        min_height="360px",
    )


# ---------------------------------------------------------------------------
# SECTION 7: Orchestration Timeline
# ---------------------------------------------------------------------------

section_title("ORCHESTRATION EVENT TIMELINE")

if timeline_data:
    fig_timeline = create_timeline_chart(
        timeline_data,
        x="minute",
        y="events",
        color="status",
        title="Governed Proposals Over Time",
        labels={"minute": "Time", "events": "Proposals", "status": "Status"},
        height=340,
    )
    st.plotly_chart(fig_timeline, use_container_width=True)
else:
    cyber_card(
        "Orchestration Timeline",
        "No timestamped governance events are available yet.",
        min_height="220px",
    )


# ---------------------------------------------------------------------------
# SECTION 8: Execution Lineage Table
# ---------------------------------------------------------------------------

section_title("EXECUTION LINEAGE")
status_badge("APPEND-ONLY TRACE", "info")
st.markdown("<br>", unsafe_allow_html=True)

if all_logs:
    _sorted_logs = sorted(
        all_logs,
        key=lambda r: r.get("timestamp") or "",
        reverse=True,
    )

    lin_col1, lin_col2, lin_col3 = st.columns([1.4, 1, 1])

    with lin_col1:
        lin_query = st.text_input(
            "Search lineage",
            placeholder="Search tool, status, session...",
        )
    with lin_col2:
        lin_status_opts = sorted({r.get("status") for r in all_logs if r.get("status")})
        lin_status = st.selectbox("Status filter", ["All Statuses", *lin_status_opts])
    with lin_col3:
        lin_verif_opts = ["All Verification", "VERIFIED", "FAILED", "PROOF_PRESENT", "NOT_AVAILABLE"]
        lin_verif = st.selectbox("Verification filter", lin_verif_opts)

    def _lin_match(row: dict[str, Any], q: str) -> bool:
        if not q:
            return True
        q = q.lower()
        fields = [row.get("session_id"), row.get("tool_name"), row.get("status"), row.get("reason")]
        return any(q in str(f).lower() for f in fields if f)

    filtered = [
        r for r in _sorted_logs
        if _lin_match(r, lin_query)
        and (lin_status == "All Statuses" or r.get("status") == lin_status)
        and (lin_verif == "All Verification" or _verification_label(r) == lin_verif)
    ]

    st.caption(f"Showing {len(filtered)} of {len(all_logs)} lineage records")

    lineage_rows = [
        {
            "timestamp":   _format_ts_full(r.get("timestamp")),
            "session":     _short_id(r.get("session_id")),
            "intent_hash": _short_id(r.get("intent_hash")),
            "tool":        r.get("tool_name", "-"),
            "status":      r.get("status", "-"),
            "verification":_verification_label(r),
        }
        for r in filtered
    ]

    if lineage_rows:
        st.dataframe(lineage_rows, use_container_width=True, hide_index=True)
    else:
        cyber_card(
            "No Matching Records",
            "Adjust filters to show lineage records.",
            min_height="120px",
        )
else:
    cyber_card(
        "No Lineage Records",
        "No governed execution records have been logged yet.",
        min_height="180px",
    )


# ---------------------------------------------------------------------------
# SECTION 9: Raw Session Record Viewer (collapsed, sanitized)
# ---------------------------------------------------------------------------

section_title("RAW SESSION RECORD VIEWER")

with st.expander("Inspect raw session proposals (sanitized, read-only)", expanded=False):
    if _full_session_ids:
        raw_selected = st.selectbox(
            "Select session to inspect",
            options=_full_session_ids,
            format_func=_short_id,
            key="raw_viewer_select",
        )
        raw_proposals = get_session_proposals(raw_selected)

        if raw_proposals:
            st.caption(
                f"Displaying {len(raw_proposals)} sanitized proposal record(s). "
                "Payload and feature fields are excluded."
            )
            st.json(raw_proposals)
        else:
            st.info("No proposal records found for this session.")
    else:
        st.info("No orchestration sessions are available to inspect.")


# ---------------------------------------------------------------------------
# SECTION 10: Intent Contract Groups
# ---------------------------------------------------------------------------

if intent_groups:
    section_title("INTENT CONTRACT COVERAGE")

    intent_rows = [
        {
            "intent_hash":     g["intent_label"],
            "total_proposals": g["total_proposals"],
            "executed":        g["executed"],
            "blocked":         g["blocked"],
            "sessions":        g["session_count"],
            "governance_rate": f"{g['governance_rate']}%",
        }
        for g in intent_groups
    ]

    st.dataframe(intent_rows, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    """
    <div style="text-align:center;color:#93A4C3;padding-bottom:2rem;font-size:0.9rem;">
        NIYAM-AI Orchestration Monitor &nbsp;•&nbsp; Read-Only Governance Observability
    </div>
    """,
    unsafe_allow_html=True,
)
