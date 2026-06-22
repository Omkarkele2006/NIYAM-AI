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
from schema.governance_service import get_system_metrics, load_audit_logs, get_zkml_metrics
from utils.audit_parser import get_verification_statistics
from schema.proof_lifecycle import validate_proof_environment
from utils.proof_reader import (
    get_latest_proof_metadata,
    get_proof_artifact_overview,
    get_verification_key_metadata,
    get_verification_status,
    get_witness_artifact,
)
from utils.theme import configure_page, load_global_css, section_title
from utils.time_utils import format_timestamp_table, parse_utc_timestamp





def _format_bytes(size: int | None) -> str:
    """Format byte counts for compact metric display."""

    if not size:
        return "0 B"

    if size < 1024:
        return f"{size} B"

    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"

    return f"{size / (1024 * 1024):.1f} MB"


def _short_hash(value: str | None, length: int = 16) -> str:
    """Return a compact hash preview."""

    if not value:
        return "-"

    return value[:length] + "..." if len(value) > length else value


def _verification_label(row: dict[str, Any]) -> str:
    """Return proof status for an audit event."""

    if row.get("verification") is True:
        return "VERIFIED"

    if row.get("verification") is False:
        return "FAILED"

    if row.get("proof"):
        return "PROOF_PRESENT"

    return "NOT_AVAILABLE"


configure_page("Proof Explorer | NIYAM-AI")
load_global_css()

section_title("ZKML PROOF EXPLORER")
status_badge("PROOF OBSERVABILITY", "info")

# Sourcing everything from centralized governance service
from schema.governance_service import (
    get_latest_verified_execution,
    get_proof_telemetry,
)

latest_verified = get_latest_verified_execution()
telemetry = get_proof_telemetry()
zkml_metrics = telemetry["metrics"]
recent_runs = telemetry["recent_runs"]

proof = get_latest_proof_metadata()
witness = get_witness_artifact()
verification = get_verification_status()
verification_key = get_verification_key_metadata()
overview = get_proof_artifact_overview()
verification_stats = get_verification_statistics()
system_metrics = get_system_metrics()
logs = load_audit_logs()

proof_events = [
    row
    for row in logs
    if row.get("proof") or row.get("verification") is not None
]

# Load live environment report for top-level status card
_live_env = validate_proof_environment()
_ezkl_ok = _live_env["ezkl_available"]

metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)

with metric_col1:
    metric_card(
        "Proof Artifact (Artifact)",
        "Present" if proof["exists"] else "Missing",
        _format_bytes(proof["size_bytes"]),
        "success" if proof["exists"] else "danger",
    )

with metric_col2:
    metric_card(
        "Witness Artifact (Artifact)",
        "Present" if witness["exists"] else "Missing",
        _format_bytes(witness["size_bytes"]),
        "success" if witness["exists"] else "danger",
    )

with metric_col3:
    st_verified = latest_verified is not None
    metric_card(
        "Latest Audited Verification (Audited)",
        "VERIFIED" if st_verified else "NOT_AVAILABLE",
        "Audited result (last verified pipeline run in database)" if st_verified else "No verified proofs yet",
        "success" if st_verified else "warning",
    )

with metric_col4:
    metric_card(
        "Historical Verified Events (Historical)",
        str(verification_stats["verified"]),
        "Audit DB rows (historical) — not live ezkl results",
        "normal",
    )

with metric_col5:
    metric_card(
        "Local Host EZKL Capability (Runtime)",
        "AVAILABLE" if _ezkl_ok else "UNAVAILABLE",
        "Current host environment check (EZKL is active in WSL, unavailable on Windows host)" if not _ezkl_ok else "Live runtime check",
        "success" if _ezkl_ok else "danger",
    )

st.markdown("<br>", unsafe_allow_html=True)

# Latest Verified Execution Panel
st.markdown("## Latest Verified Execution")
if latest_verified:
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        cyber_card(
            "Latest Audited Proof Metadata",
            f"""
            • <b>Execution ID:</b> {latest_verified.get('execution_id', '-')}<br><br>
            • <b>Session ID:</b> {latest_verified.get('session_id', '-')}<br><br>
            • <b>Proof Hash:</b> {_short_hash(latest_verified.get('proof_hash'), 32)}<br><br>
            • <b>Witness Hash:</b> {_short_hash(latest_verified.get('witness_hash'), 32)}<br><br>
            • <b>Input Hash:</b> {_short_hash(latest_verified.get('input_hash'), 32)}<br><br>
            • <b>Verification Timestamp:</b> {latest_verified.get('timestamp', '-')}
            """,
            min_height="320px",
        )
    with col_l2:
        cyber_card(
            "Latest Audited Execution Performance",
            f"""
            • <b>Verification Result:</b> <strong style="color:#00FF88;">VERIFIED</strong><br><br>
            • <b>Witness Latency:</b> {latest_verified.get('witness_generation_ms', 0) or 0:.1f} ms<br><br>
            • <b>Proof Latency:</b> {latest_verified.get('proof_generation_ms', 0) or 0:.1f} ms<br><br>
            • <b>Verification Latency:</b> {latest_verified.get('verification_ms', 0) or 0:.1f} ms<br><br>
            • <b>Total Pipeline Latency:</b> {latest_verified.get('total_proof_pipeline_ms', 0) or 0:.1f} ms
            """,
            min_height="320px",
        )
else:
    cyber_card(
        "No Verified Executions Found",
        "No verified executions were found in the SQLite audit database. Execute a governed tool call to generate a valid cryptographic proof.",
        min_height="180px",
    )

st.markdown("<br>", unsafe_allow_html=True)

st.markdown("### zkML Pipeline Performance")
perf_col1, perf_col2, perf_col3, perf_col4 = st.columns(4)
with perf_col1:
    metric_card(
        "Avg Witness Latency (Audited)",
        f"{zkml_metrics['witness_generation']['avg']:.1f} ms",
        "EZKL witness processing",
        "warning"
    )
with perf_col2:
    metric_card(
        "Avg Proving Latency (Audited)",
        f"{zkml_metrics['proof_generation']['avg']:.1f} ms",
        "EZKL proof generation",
        "warning"
    )
with perf_col3:
    metric_card(
        "Avg Verification Latency (Audited)",
        f"{zkml_metrics['verification']['avg']:.1f} ms",
        "EZKL verification",
        "success"
    )
with perf_col4:
    metric_card(
        "Avg Pipeline Latency (Audited)",
        f"{zkml_metrics['total_pipeline']['avg']:.1f} ms",
        "Total zkML pipeline run time",
        "normal"
    )

st.markdown("<br>", unsafe_allow_html=True)

section_title("LATEST PROOF METADATA")

proof_col1, proof_col2 = st.columns([1, 1])

with proof_col1:
    if proof["exists"]:
        cyber_card(
            "Proof Artifact Status",
            f"""
            Path: {proof["path"]}<br>
            Size: {_format_bytes(proof["size_bytes"])}<br>
            Modified: {proof.get("modified_at") or "-"}<br>
            SHA-256: {_short_hash(proof.get("sha256"), 28)}
            """,
            min_height="260px",
        )
    else:
        cyber_card(
            "Proof Artifact Missing",
            "No proof.json artifact is currently available. Run a governed action that reaches the zkML proof stage.",
            min_height="260px",
        )

with proof_col2:
    if witness["exists"]:
        cyber_card(
            "Witness Artifact Status",
            f"""
            Path: {witness["path"]}<br>
            Size: {_format_bytes(witness["size_bytes"])}<br>
            Modified: {witness.get("modified_at") or "-"}<br>
            SHA-256: {_short_hash(witness.get("sha256"), 28)}
            """,
            min_height="260px",
        )
    else:
        cyber_card(
            "Witness Artifact Missing",
            "No witness.json artifact is currently available. Proof inspection will be limited until witness generation succeeds.",
            min_height="260px",
        )

section_title("VERIFICATION KEY AND PROOF STATUS")

vk_col1, vk_col2 = st.columns([1, 1])

with vk_col1:
    cyber_card(
        "Verification Key",
        f"""
        VK present: {verification_key["exists"]}<br>
        VK size: {_format_bytes(verification_key["size_bytes"])}<br>
        VK SHA-256: {_short_hash(verification_key.get("sha256"), 36)}
        """,
        min_height="240px",
    )

with vk_col2:
    status_kind = "success" if latest_verified else "danger"
    cyber_card(
        "Latest Audited Verification (Historical Audit Record)",
        f"""
        Status: {"VERIFIED" if latest_verified else "NOT_AVAILABLE"}<br>
        Verified: {st_verified} (Historical execution verified in database)<br>
        Proof Path: {latest_verified.get('proof_archive_path', '-') if latest_verified else "-"}<br>
        Error: None
        """,
        min_height="240px",
    )
    status_badge("VERIFIED" if latest_verified else "NOT_AVAILABLE", status_kind)

section_title("PROOF-RELATED GOVERNANCE METRICS")

verify_rows = [
    {"status": "Verified", "count": verification_stats["verified"]},
    {"status": "Failed", "count": verification_stats["failed"]},
    {"status": "Missing", "count": verification_stats["missing"]},
]

chart_col1, chart_col2 = st.columns([1, 1])

with chart_col1:
    fig_verification = px.bar(
        verify_rows,
        x="status",
        y="count",
        title="Audit Records by Proof Verification State",
        labels={"status": "Verification State", "count": "Records"},
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

with chart_col2:
    artifact_rows = [
        {"artifact": "Proof", "size_bytes": proof["size_bytes"]},
        {"artifact": "Witness", "size_bytes": witness["size_bytes"]},
        {"artifact": "Verification Key", "size_bytes": verification_key["size_bytes"]},
    ]

    fig_artifacts = px.bar(
        artifact_rows,
        x="artifact",
        y="size_bytes",
        title="Proof System Artifact Sizes",
        labels={"artifact": "Artifact", "size_bytes": "Bytes"},
        color="artifact",
        color_discrete_sequence=["#00D1FF", "#9D4EDD", "#FFC857"],
    )
    fig_artifacts.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#E6F1FF",
        height=340,
        showlegend=False,
    )
    st.plotly_chart(fig_artifacts, use_container_width=True)

section_title("PROOF EXECUTION TIMELINE")

timeline_rows = [
    {
        "timestamp": parse_utc_timestamp(row.get("timestamp")),
        "verification": _verification_label(row),
        "tool": row.get("tool_name", "unknown"),
    }
    for row in proof_events
    if parse_utc_timestamp(row.get("timestamp")) is not None
]

if timeline_rows:
    timeline_counts = Counter(
        (
            format_timestamp_table(row.get("timestamp")).replace(" IST", ""),
            row["verification"],
        )
        for row in timeline_rows
    )
    chart_rows = [
        {"minute": minute, "verification": status, "events": count}
        for (minute, status), count in timeline_counts.items()
    ]

    fig_timeline = px.line(
        chart_rows,
        x="minute",
        y="events",
        color="verification",
        markers=True,
        title="Proof Events Over Time",
        labels={"minute": "Time", "events": "Events", "verification": "Proof State"},
        color_discrete_map={
            "VERIFIED": "#00FF88",
            "FAILED": "#FF3B5C",
            "PROOF_PRESENT": "#00D1FF",
            "NOT_AVAILABLE": "#93A4C3",
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
        "Proof Timeline",
        "No timestamped proof-related audit events are available yet.",
        min_height="220px",
    )

section_title("JSON INSPECTORS")

inspect_col1, inspect_col2 = st.columns([1, 1])

with inspect_col1:
    with st.expander("proof.json", expanded=False):
        if proof["exists"] and proof.get("data") is not None:
            st.json(proof["data"])
        else:
            st.info("proof.json is missing or could not be parsed.")

with inspect_col2:
    with st.expander("witness.json", expanded=False):
        if witness["exists"] and witness.get("data") is not None:
            st.json(witness["data"])
        else:
            st.info("witness.json is missing or could not be parsed.")

with st.expander("Proof Observability Snapshot", expanded=False):
    st.json(
        {
            "overview": overview,
            "system_artifacts": system_metrics.get("artifacts", {}),
        }
    )
