import sys
from typing import Any
from pathlib import Path
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from schema.governance_service import load_audit_logs, get_decision_timeline, get_execution_forensics
from utils.theme import configure_page, load_global_css, section_title, cyber_header
from components.cards import cyber_card, status_badge
from utils.time_utils import format_timestamp_short

configure_page("Decision Explorer | NIYAM-AI")
load_global_css()

cyber_header(
    "DECISION EXPLORER",
    "Explainable AI governance timeline and verification audit trail"
)

status_badge("GOVERNANCE TRACEABILITY SYSTEM", "success")

st.markdown("<br>", unsafe_allow_html=True)

# Helper to render styled timeline steps
def render_timeline_step(index: int, label: str, state: str, status: str, duration: float | None = None):
    # status: "success" (green), "danger" (red), "warning" (yellow), "idle" (grey)
    colors = {
        "success": {"border": "#00FF88", "bg": "rgba(0, 255, 136, 0.08)", "text": "#00FF88"},
        "danger": {"border": "#FF3B5C", "bg": "rgba(255, 59, 92, 0.08)", "text": "#FF3B5C"},
        "warning": {"border": "#FFC857", "bg": "rgba(255, 200, 87, 0.08)", "text": "#FFC857"},
        "idle": {"border": "#4F6380", "bg": "rgba(79, 99, 128, 0.08)", "text": "#93A4C3"}
    }
    c = colors.get(status, colors["idle"])
    dur_str = f" ({duration:.1f} ms)" if duration is not None else ""
    
    st.markdown(
        f"""
        <div style="
            position: relative;
            padding: 0.95rem 1.1rem;
            margin-bottom: 0.85rem;
            border-left: 4px solid {c['border']};
            background: {c['bg']};
            border-top: 1px solid rgba(255,255,255,0.06);
            border-right: 1px solid rgba(255,255,255,0.06);
            border-bottom: 1px solid rgba(255,255,255,0.06);
            border-radius: 8px;
        ">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-family:'Orbitron', sans-serif; font-size:0.75rem; color:#93A4C3;">STEP {index:02d}</span>
                <span style="font-size:0.8rem; font-weight:700; color:{c['text']}; text-transform:uppercase;">{status}</span>
            </div>
            <div style="color:#E6F1FF; font-weight:700; font-size:0.95rem; margin-top:0.35rem;">{label}{dur_str}</div>
            <div style="color:#93A4C3; font-size:0.85rem; margin-top:0.25rem;">{state}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# Load audit events
logs = load_audit_logs()

# We identify unique tool execution attempts by filtering for events that represent
# interceptor blocks, execution results, or step logs, grouping them by session_id and action_hash
execution_decisions = []
seen_decisions = set()

# Process events in reverse chronological order to list recent ones first
for row in reversed(logs):
    sess_id = row.get("session_id")
    act_hash = row.get("action_hash")
    tool = row.get("tool_name")
    status = row.get("status")
    
    if sess_id and act_hash and tool:
        dec_key = (sess_id, act_hash)
        if dec_key not in seen_decisions:
            seen_decisions.add(dec_key)
            execution_decisions.append({
                "session_id": sess_id,
                "action_hash": act_hash,
                "tool_name": tool,
                "status": status or "BLOCKED",
                "timestamp": row.get("timestamp"),
                "policy": row.get("policy"),
                "reason": row.get("reason"),
                "execution_id": row.get("execution_id")
            })

if not execution_decisions:
    st.info("No tool execution decisions have been logged in the audit trail yet. Use the 'Governed Execution' page to run tool requests.")
else:
    # Sidebar selection list
    st.subheader("Select Decision Event")
    
    decision_options = [
        f"[{dec['status']}] {dec['tool_name']} - {format_timestamp_short(dec['timestamp'])}"
        for dec in execution_decisions
    ]
    
    selected_idx = st.selectbox(
        "Choose an execution attempt to analyze:",
        range(len(execution_decisions)),
        format_func=lambda i: decision_options[i]
    )
    
    selected_dec = execution_decisions[selected_idx]
    
    st.markdown("---", unsafe_allow_html=True)
    
    # Grid of details
    det_col1, det_col2 = st.columns(2)
    with det_col1:
        st.markdown(f"**Tool Invocation:** `{selected_dec['tool_name']}`")
        st.markdown(f"**Session ID:** `{selected_dec['session_id'][:12]}...`")
        st.markdown(f"**Action Hash:** `{selected_dec['action_hash'][:18]}...`")
    with det_col2:
        st.markdown(f"**Timestamp:** `{selected_dec['timestamp']}`")
        st_color = "success" if selected_dec["status"] == "EXECUTED" else "danger"
        st.markdown(f"**Decision Status:**")
        status_badge(selected_dec["status"], st_color)
        if selected_dec.get("policy"):
            st.markdown(f"**Applied Policy:** `{selected_dec['policy']}`")

    st.markdown("<br>", unsafe_allow_html=True)

    # Add expandable "Execution Forensics" panel
    exec_id = selected_dec.get("execution_id") or selected_dec.get("session_id")
    forensics = get_execution_forensics(exec_id)
    if forensics:
        with st.expander("🔍 View Execution Forensics", expanded=False):
            st.markdown("### Cryptographic Hashes & Identifiers")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.markdown(f"**Execution ID:** `{forensics.get('execution_id', '-')}`")
                st.markdown(f"**Session ID:** `{forensics.get('session_id', '-')}`")
                st.markdown(f"**Action Hash:** `{forensics.get('action_hash', '-')}`")
                st.markdown(f"**Intent Hash:** `{forensics.get('intent_hash', '-')}`")
            with col_f2:
                st.markdown(f"**Proof Hash:** `{forensics.get('proof_hash', '-')}`")
                st.markdown(f"**Witness Hash:** `{forensics.get('witness_hash', '-')}`")
                st.markdown(f"**Input Hash:** `{forensics.get('input_hash', '-')}`")
                st.markdown(f"**Chain Integrity Status:** `{forensics.get('audit_chain_status', '-')}`")
                
            st.markdown("### Execution & Proving Latencies")
            col_f3, col_f4 = st.columns(2)
            with col_f3:
                w_ms = forensics.get("witness_generation_ms")
                st.markdown(f"**Witness Generation Time:** `{f'{w_ms:.1f} ms' if w_ms is not None else '-'}`")
                p_ms = forensics.get("proof_generation_ms")
                st.markdown(f"**Proof Generation Time:** `{f'{p_ms:.1f} ms' if p_ms is not None else '-'}`")
            with col_f4:
                v_ms = forensics.get("verification_ms")
                st.markdown(f"**Verification Time:** `{f'{v_ms:.1f} ms' if v_ms is not None else '-'}`")
                t_ms = forensics.get("total_proof_pipeline_ms")
                st.markdown(f"**Total zkML Pipeline Time:** `{f'{t_ms:.1f} ms' if t_ms is not None else '-'}`")
                
            if forensics.get("proof_archive_path"):
                st.markdown(f"**Proof Archive Path:** `{forensics.get('proof_archive_path')}`")

    st.markdown("<br>", unsafe_allow_html=True)
    section_title("GOVERNANCE TIMELINE TRACE")
    st.caption("Chronological validation sequence performed by the security interceptor:")

    # Retrieve ordered timeline events for this execution/session
    timeline_events = get_decision_timeline(exec_id)

    def map_event_to_step_info(event: dict[str, Any]) -> tuple[str, str, str, float | None]:
        event_type = event.get("event_type")
        status_val = event.get("status")
        state_val = event.get("state")
        
        # Defaults
        label_str = event_type or f"Governance Event ({status_val or 'INFO'})"
        desc_str = event.get("detail") or event.get("reason") or f"Status: {status_val or 'unknown'}"
        step_status = "idle"
        dur_val = None
        
        # Duration checks
        if "duration_ms" in event and event["duration_ms"] is not None:
            dur_val = event["duration_ms"]
        elif "generation_duration_ms" in event and event["generation_duration_ms"] is not None:
            dur_val = event["generation_duration_ms"]
        elif "verification_duration_ms" in event and event["verification_duration_ms"] is not None:
            dur_val = event["verification_duration_ms"]

        # Map event_type
        if event_type == "POLICY_LOADED":
            label_str = "Governance Policy Loaded"
            step_status = "success" if status_val == "SUCCESS" else "danger"
        elif event_type == "POLICY_VALIDATED":
            label_str = "Policy Schema Validated"
            step_status = "success" if status_val == "SUCCESS" else "danger"
        elif event_type == "POLICY_REJECTED":
            label_str = "Policy Schema Rejected"
            step_status = "danger"
        elif event_type == "POLICY_SEALED":
            label_str = "Intent Contract Sealed"
            step_status = "success"
        elif event_type == "POLICY_VERSION_ACTIVATED":
            label_str = "Policy Version Activated"
            step_status = "success"
        elif event_type == "POLICY_VERSION_DEACTIVATED":
            label_str = "Policy Version Deactivated"
            step_status = "warning"
        elif event_type == "PROOF_ENVIRONMENT_INVALID":
            label_str = "zkML Environment Validation"
            step_status = "danger"
        elif event_type == "FEATURE_DIMENSION_MISMATCH":
            label_str = "Feature Dimension Mismatch"
            step_status = "danger"
        elif event_type == "PROOF_GENERATION_STARTED":
            label_str = "zkML Proof Generation Started"
            step_status = "warning"
        elif event_type == "PROOF_GENERATION_COMPLETED":
            label_str = "zkML Proof Generated"
            step_status = "success"
            if not dur_val and "generation_duration_ms" in event:
                dur_val = event["generation_duration_ms"]
        elif event_type == "PROOF_GENERATION_FAILED":
            label_str = "zkML Proof Generation Failed"
            step_status = "danger"
        elif event_type == "PROOF_GENERATION_TIMEOUT":
            label_str = "zkML Proof Generation Timeout"
            step_status = "danger"
        elif event_type == "WITNESS_GENERATION_TIMEOUT":
            label_str = "Witness Generation Timeout"
            step_status = "danger"
        elif event_type == "PROOF_VERIFICATION_STARTED":
            label_str = "Cryptographic Proof Verification Started"
            step_status = "warning"
        elif event_type == "PROOF_VERIFICATION_COMPLETED":
            label_str = "Cryptographic Proof Verified"
            step_status = "success"
            if not dur_val and "verification_duration_ms" in event:
                dur_val = event["verification_duration_ms"]
        elif event_type == "PROOF_VERIFICATION_FAILED":
            label_str = "Cryptographic Proof Verification Failed"
            step_status = "danger"
        elif event_type == "PROOF_EXECUTION_BLOCKED":
            label_str = "Governance Execution Blocked"
            step_status = "danger"
        elif event_type == "EXECUTION_STARTED":
            label_str = "Isolated Process Execution Started"
            step_status = "warning"
        elif event_type == "EXECUTION_COMPLETED":
            label_str = "Isolated Process Execution Completed"
            step_status = "success"
        elif event_type == "EXECUTION_TERMINATED":
            label_str = "Isolated Process Execution Terminated"
            step_status = "danger"
        elif event_type == "CLEANUP_COMPLETED":
            label_str = "Runtime Cleanup Completed"
            step_status = "success"
        elif event_type == "CLEANUP_FAILED":
            label_str = "Runtime Cleanup Failed"
            step_status = "danger"
        else:
            # Fallback to checking status/state if no event_type matching
            if status_val == "EXECUTED" or state_val == "COMPLETED" or event.get("status") == "EXECUTED":
                label_str = "Isolated Process Execution"
                step_status = "success"
                desc_str = "Tool dispatched inside isolated SubprocessSandboxExecutor memory boundary."
            elif status_val == "BLOCKED" or state_val == "FAILED" or event.get("status") == "BLOCKED":
                label_str = "Governance Action Blocked"
                step_status = "danger"
                desc_str = event.get("reason") or "Fail-closed policy enforced - execution prevented."

        return label_str, desc_str, step_status, dur_val

    # Loop through events in chronological order and render steps dynamically
    if not timeline_events:
        st.warning("No timeline events found for this selection.")
    else:
        for idx, event in enumerate(timeline_events, start=1):
            lbl, desc, step_st, duration = map_event_to_step_info(event)
            render_timeline_step(idx, lbl, desc, step_st, duration=duration)
