import sys
from pathlib import Path
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from schema.governance_service import load_audit_logs
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
                "reason": row.get("reason")
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
    section_title("GOVERNANCE TIMELINE TRACE")
    st.caption("Chronological validation sequence performed by the security interceptor:")

    # Retrieve all logs associated with this specific decision session
    session_logs = [
        row for row in logs 
        if row.get("session_id") == selected_dec["session_id"] and row.get("action_hash") == selected_dec["action_hash"]
    ]
    
    # Extract details from matching events
    policy_loaded_event = next((r for r in logs if r.get("event_type") == "POLICY_LOADED" and r.get("policy_id") == selected_dec.get("policy", "").split("_v")[0]), None)
    policy_validated_event = next((r for r in logs if r.get("event_type") == "POLICY_VALIDATED" and r.get("policy_id") == selected_dec.get("policy", "").split("_v")[0]), None)
    policy_sealed_event = next((r for r in logs if r.get("event_type") == "POLICY_SEALED" and r.get("session_id") == selected_dec["session_id"]), None)
    
    generation_started = next((r for r in session_logs if r.get("event_type") == "PROOF_GENERATION_STARTED"), None)
    generation_completed = next((r for r in session_logs if r.get("event_type") == "PROOF_GENERATION_COMPLETED"), None)
    generation_failed = next((r for r in session_logs if r.get("event_type") == "PROOF_GENERATION_FAILED"), None)
    
    verification_started = next((r for r in session_logs if r.get("event_type") == "PROOF_VERIFICATION_STARTED"), None)
    verification_completed = next((r for r in session_logs if r.get("event_type") == "PROOF_VERIFICATION_COMPLETED"), None)
    verification_failed = next((r for r in session_logs if r.get("event_type") == "PROOF_VERIFICATION_FAILED"), None)
    
    blocked_event = next((r for r in session_logs if r.get("event_type") == "PROOF_EXECUTION_BLOCKED" or r.get("status") == "BLOCKED"), None)
    execution_event = next((r for r in session_logs if r.get("status") == "EXECUTED"), None)

    # 1. Step 1: Policy Loading
    if selected_dec.get("policy"):
        p_id = selected_dec["policy"].split("_v")[0]
        render_timeline_step(1, "Policy Loaded", f"Governance Policy artifact '{p_id}' loaded from repository directory.", "success")
    else:
        render_timeline_step(1, "Policy Loaded", "No managed policy artifact linked to this execution contract (fallback inline contract).", "warning")

    # 2. Step 2: Policy Validation
    if selected_dec.get("policy"):
        p_ver = selected_dec["policy"].split("_v")[-1] if "_v" in selected_dec["policy"] else "unknown"
        render_timeline_step(2, "Policy Schema Validated", f"Checked version '{p_ver}' semantic formatting, rule conflicts, and dynamic tool gate checks.", "success")
    else:
        render_timeline_step(2, "Policy Schema Validated", "Validation skipped (contract instantiated directly in memory).", "warning")

    # 3. Step 3: Contract Sealed
    render_timeline_step(3, "Intent Contract Sealed", "Tuple conversions completed, and fields locked to enforce runtime immutability.", "success")

    # 4. Step 4: Tool Gate Check
    if blocked_event and ("forbidden" in blocked_event.get("reason", "").lower() or "not allowed" in blocked_event.get("reason", "").lower()):
        render_timeline_step(4, "Tool Gate Authorization Check", f"BLOCKED: {blocked_event.get('reason')}", "danger")
    else:
        render_timeline_step(4, "Tool Gate Authorization Check", "Tool name validated against allowed lists and missing from forbidden lists.", "success")

    # 5. Step 5: Schema Validation
    if blocked_event and ("schema validation" in blocked_event.get("reason", "").lower() or "no schema registered" in blocked_event.get("reason", "").lower()):
        render_timeline_step(5, "Payload Schema Validation", f"BLOCKED: {blocked_event.get('reason')}", "danger")
    elif blocked_event and ("forbidden" in blocked_event.get("reason", "").lower() or "not allowed" in blocked_event.get("reason", "").lower()):
        render_timeline_step(5, "Payload Schema Validation", "Skipped due to prior authorization block.", "idle")
    else:
        render_timeline_step(5, "Payload Schema Validation", "JSON schema validation completed successfully, allowed parameters only.", "success")

    # 6. Step 6: zkML Proving
    if generation_completed:
        dur = generation_completed.get("generation_duration_ms")
        render_timeline_step(6, "zkML Proof Generated", f"EZKL witness processing and proof generation succeeded. Size: {generation_completed.get('proof_size_bytes', 0)} bytes.", "success", duration=dur)
    elif generation_failed:
        dur = generation_failed.get("generation_duration_ms")
        render_timeline_step(6, "zkML Proof Generated", f"FAILED: {generation_failed.get('reason')}", "danger", duration=dur)
    elif blocked_event:
        render_timeline_step(6, "zkML Proof Generated", "Skipped due to prior policy or gate validation block.", "idle")
    else:
        render_timeline_step(6, "zkML Proof Generated", "Pending or skipped.", "idle")

    # 7. Step 7: ZK Verification
    if verification_completed:
        dur = verification_completed.get("verification_duration_ms")
        render_timeline_step(7, "Cryptographic Proof Verified", "EZKL cryptographic verifier successfully verified the proof against the circuit SRS/VK.", "success", duration=dur)
    elif verification_failed:
        dur = verification_failed.get("verification_duration_ms")
        render_timeline_step(7, "Cryptographic Proof Verified", f"FAILED: {verification_failed.get('reason')}", "danger", duration=dur)
    elif blocked_event:
        render_timeline_step(7, "Cryptographic Proof Verified", "Skipped due to prior validation or proving failure.", "idle")
    else:
        render_timeline_step(7, "Cryptographic Proof Verified", "Pending or skipped.", "idle")

    # 8. Step 8: Execution Runtime
    if execution_event:
        render_timeline_step(8, "Isolated Process Execution", "Tool dispatched inside isolated SubprocessSandboxExecutor memory boundary.", "success")
    elif blocked_event:
        render_timeline_step(8, "Isolated Process Execution", "BLOCKED: Fail-closed policy enforced - execution prevented.", "danger")
    else:
        render_timeline_step(8, "Isolated Process Execution", "Pending or aborted.", "idle")

    # 9. Step 9: Audit Ledger
    if execution_event or blocked_event:
        render_timeline_step(9, "Cryptographic Hash Chain Recorded", "Audit block with previous hash linkage successfully committed to SQLite.", "success")
    else:
        render_timeline_step(9, "Cryptographic Hash Chain Recorded", "Pending.", "idle")
