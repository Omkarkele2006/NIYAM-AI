"""
Governed Execution Console — NIYAM-AI.

This is NOT a chatbot.  It is a governed intent submission console where every
user prompt passes through the full interceptor pipeline:

    prompt → IntentContract → SecurePlanner → proposals
    → interceptor → CFI → gate → ML features → proof → verify → execute/block
    → audit log

Governance boundaries enforced in this file:
  - No direct tool execution — all execution flows through the interceptor
  - No registry exposure — registry is created inside the button handler only
  - No payload rendering — only payload key names are shown, never values
  - No feature vector rendering
  - No proof data rendering — only status (VERIFIED / FAILED)
  - No autonomous loops — controller.orchestrate() runs exactly once per click
  - Planner receives no registry, no execute_func, no runtime reference
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = FRONTEND_ROOT.parent

for _path in (REPO_ROOT, FRONTEND_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from components.cards import cyber_card, metric_card, status_badge
from schema.governance_service import load_audit_logs
from utils.theme import configure_page, load_global_css, section_title, page_header


# ---------------------------------------------------------------------------
# Governance profiles — predefined policy bundles for demo clarity
# ---------------------------------------------------------------------------

GOVERNANCE_PROFILES: dict[str, dict[str, Any]] = {
    "SAFE_DEFAULT": {
        "description": "Standard governance — allows transactions, blocks email exfiltration.",
        "allowed_tools": ["proceed_transaction"],
        "forbidden_tools": ["send_email"],
        "risk_label": "MODERATE",
    },
    "READ_ONLY": {
        "description": "Observation-only mode — all tool execution is forbidden.",
        "allowed_tools": [],
        "forbidden_tools": ["proceed_transaction", "send_email", "execute_code", "file_write"],
        "risk_label": "MINIMAL",
    },
    "STRICT_GOVERNANCE": {
        "description": "High-security — expanded forbidden list, proof-verified transactions only.",
        "allowed_tools": ["proceed_transaction"],
        "forbidden_tools": ["send_email", "execute_code", "file_write", "shell_exec"],
        "risk_label": "HIGH ENFORCEMENT",
    },
    "FINANCIAL_SAFE_MODE": {
        "description": "Financial operations under full zkML proof verification.",
        "allowed_tools": ["proceed_transaction"],
        "forbidden_tools": ["send_email"],
        "risk_label": "FINANCIAL",
    },
}


# ---------------------------------------------------------------------------
# Demo tool handlers — pure, side-effect-free, governance-safe
# ---------------------------------------------------------------------------

def _demo_transaction(payload: dict[str, Any]) -> dict[str, Any]:
    """Demo handler — returns a governance-approved receipt, no real side effect."""
    return {
        "status": "GOVERNANCE_APPROVED",
        "tool": "proceed_transaction",
        "amount": payload.get("amount", 0),
        "recipient": payload.get("recipient", "unknown"),
        "note": "Executed under proof-verified governance runtime.",
    }


def _demo_email(payload: dict[str, Any]) -> dict[str, Any]:
    """Demo handler — should be blocked by most governance profiles."""
    return {
        "status": "SENT",
        "tool": "send_email",
        "note": "This should not appear if governance is enforced.",
    }


# ---------------------------------------------------------------------------
# Pipeline builder — creates a fresh governance pipeline per submission
# ---------------------------------------------------------------------------

def _build_and_run(user_prompt: str, profile_name: str) -> dict[str, Any]:
    """Build a complete governance pipeline and run one orchestration cycle.

    The entire pipeline (contract, CFI, gate, planner, registry, controller)
    is created fresh inside this function.  Nothing persists beyond the return
    value, ensuring no execution authority leaks into session state.
    """

    # Lazy imports to avoid circular dependency through __init__.py
    from schema.intent_contract import IntentContract
    from schema.control_flow import ControlFlowIntegrity
    from schema.tool_gate import ToolAuthorityGate
    from schema.orchestration.controller import GovernanceOrchestrationController
    from schema.orchestration.secure_planner import RuleBasedSecurePlanner
    from schema.orchestration.tool_registry import GovernedToolMetadata, GovernedToolRegistry

    profile = GOVERNANCE_PROFILES[profile_name]

    # 1. Intent contract
    contract = IntentContract(
        agent_name="niyam-governance-agent",
        user_task=user_prompt,
        allowed_tools=profile["allowed_tools"],
        forbidden_tools=profile["forbidden_tools"],
    )
    contract.seal()

    # 2. Control flow integrity — sequence matches the tools the planner may emit
    cfi_sequence = list(profile["allowed_tools"]) or ["proceed_transaction"]
    cfi = ControlFlowIntegrity(allowed_sequence=cfi_sequence)

    # 3. Tool authority gate
    gate = ToolAuthorityGate(contracts=contract)

    # 4. Planner (proposal-only, zero execution authority)
    planner = RuleBasedSecurePlanner()

    # 5. Tool registry (private to this function scope)
    registry = GovernedToolRegistry()
    registry.register(
        metadata=GovernedToolMetadata(
            name="proceed_transaction",
            description="Process a governed financial transaction.",
            risk_level="MEDIUM",
            allowed_payload_keys=("amount", "recipient", "data"),
            requires_proof=True,
            timeout_seconds=10,
        ),
        handler=_demo_transaction,
    )
    registry.register(
        metadata=GovernedToolMetadata(
            name="send_email",
            description="Send an email (typically forbidden).",
            risk_level="HIGH",
            allowed_payload_keys=("to", "data"),
            requires_proof=True,
            timeout_seconds=5,
        ),
        handler=_demo_email,
    )

    # 6. Controller — bridges planner to interceptor
    controller = GovernanceOrchestrationController(
        planner=planner,
        tool_registry=registry,
        contract=contract,
        cfi=cfi,
        gate=gate,
    )

    # 7. Run exactly one orchestration cycle
    orch_result = controller.orchestrate(user_prompt=user_prompt, stop_on_block=True)

    # 8. Build a display-safe summary (no callables, no raw payloads)
    contract_summary = {
        "session_id": contract.session_id,
        "session_id_short": contract.session_id[:14] + "...",
        "intent_hash": contract.intent_hash(),
        "intent_hash_short": contract.intent_hash()[:14] + "...",
        "allowed_tools": list(profile["allowed_tools"]),
        "forbidden_tools": list(profile["forbidden_tools"]),
        "sealed": True,
    }

    records_safe = []
    for rec in orch_result.records:
        p = rec.proposal
        records_safe.append({
            "proposal_id": p.proposal_id[:14] + "...",
            "tool_name": p.tool_name,
            "rationale": p.rationale,
            "expected_effect": p.expected_effect,
            "risk_notes": p.risk_notes,
            "status": rec.status,
            "success": rec.success,
            "error": rec.error,
            "result_keys": list(rec.result.keys()) if isinstance(rec.result, dict) else None,
            "result_status": rec.result.get("status") if isinstance(rec.result, dict) else None,
        })

    planner_summary = {
        "task": orch_result.planner_output.task,
        "reasoning": orch_result.planner_output.reasoning_summary,
        "proposal_count": len(orch_result.planner_output.proposals),
    }

    return {
        "status": orch_result.status,
        "contract": contract_summary,
        "planner": planner_summary,
        "records": records_safe,
        "profile": profile_name,
        "session_id": contract.session_id,
    }


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _status_color(status: str) -> str:
    return {
        "COMPLETED": "#10B981", "EXECUTED": "#10B981",
        "BLOCKED": "#F43F5E",  "REJECTED": "#F43F5E",
        "ERROR":    "#F59E0B",
        "NO_PROPOSALS": "#4B5563", "PARTIAL": "#F59E0B",
    }.get(status, "#22D3EE")


def _status_type(status: str) -> str:
    return {
        "COMPLETED": "success", "EXECUTED": "success",
        "BLOCKED":   "danger",  "REJECTED": "danger",
        "ERROR":     "warning",
    }.get(status, "info")


def _render_proposal_card(rec: dict[str, Any]) -> None:
    """Render one proposal outcome card."""
    color = _status_color(rec["status"])
    risk_str = ", ".join(rec.get("risk_notes", [])) or "none"

    st.markdown(f"""
<div style="background:var(--bg-card);border:1px solid var(--border);border-left:3px solid {color};
border-radius:10px;padding:0.9rem 1.05rem;margin-bottom:0.65rem;">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <strong style="color:{color};font-size:0.88rem;">{rec['status']}</strong>
    <span style="color:#6B7280;font-size:0.75rem;">ID: {rec['proposal_id']}</span>
  </div>
  <div style="color:#E6E9EF;margin-top:0.45rem;font-size:0.9rem;">
    Tool: <b>{rec['tool_name']}</b>
  </div>
  <div style="color:#9AA3B2;font-size:0.82rem;margin-top:0.3rem;">{rec['rationale']}</div>
  <div style="color:#6B7280;font-size:0.78rem;margin-top:0.3rem;">Risk: {risk_str}</div>
  {"<div style='color:#F43F5E;font-size:0.82rem;margin-top:0.4rem;'>⚠ " + rec['error'] + "</div>" if rec.get('error') else ""}
</div>
""", unsafe_allow_html=True)


def _render_pipeline_stage(label: str, passed: bool, blocked: bool = False) -> str:
    """Return HTML for one pipeline stage indicator using enterprise CSS classes."""
    if blocked:
        cls, icon = "block", "✕"
    elif passed:
        cls, icon = "pass", "✓"
    else:
        cls, icon = "pending", "○"

    return f"""
<div class="pipeline-stage {cls}">
  <div class="stage-dot {cls}">{icon}</div>
  <div class="stage-label">{label}</div>
</div>"""


# ===========================================================================
# PAGE
# ===========================================================================

configure_page("Governed Execution | NIYAM-AI")
load_global_css()

page_header(
    "Governed Execution Console",
    "Every prompt passes through the full interceptor pipeline: Intent → Proof → Verify → Execute",
    badge_label="PROOF-GATED EXECUTION",
    badge_kind="success",
)


# ---------------------------------------------------------------------------
# Input section
# ---------------------------------------------------------------------------

input_col, profile_col = st.columns([1.6, 1])

with input_col:
    user_prompt = st.text_area(
        "Enter governed prompt",
        placeholder="e.g. Process a transaction of Rs 500 to user1",
        height=120,
        key="governed_prompt",
    )

with profile_col:
    profile_name = st.selectbox(
        "Governance profile",
        options=list(GOVERNANCE_PROFILES.keys()),
        index=0,
        key="gov_profile",
    )
    prof = GOVERNANCE_PROFILES[profile_name]
    cyber_card(
        f"Profile: {profile_name}",
        f"""
        {prof['description']}<br><br>
        <b>Allowed:</b> {', '.join(prof['allowed_tools']) or 'none'}<br>
        <b>Forbidden:</b> {', '.join(prof['forbidden_tools']) or 'none'}<br>
        <b>Risk level:</b> {prof['risk_label']}
        """,
        min_height="140px",
    )

st.markdown("<br>", unsafe_allow_html=True)

submitted = st.button(
    "⚡ Submit to Governance Pipeline",
    type="primary",
    key="submit_governance",
)

if submitted and user_prompt.strip():
    with st.spinner("Running governed execution pipeline..."):
        try:
            result = _build_and_run(user_prompt.strip(), profile_name)
            st.session_state["gov_exec_result"] = result
        except Exception as exc:
            st.session_state["gov_exec_result"] = {
                "status": "ERROR",
                "contract": {},
                "planner": {},
                "records": [],
                "profile": profile_name,
                "session_id": None,
                "fatal_error": str(exc),
            }
elif submitted:
    st.warning("Please enter a prompt before submitting.")


# ---------------------------------------------------------------------------
# Results rendering (only if a result exists in session state)
# ---------------------------------------------------------------------------

result = st.session_state.get("gov_exec_result")

if result:
    st.markdown("<br>", unsafe_allow_html=True)

    # -- Fatal error handling --
    if result.get("fatal_error"):
        st.error(f"Pipeline error: {result['fatal_error']}")

    # -- Orchestration status --
    section_title("GOVERNANCE DECISION")
    orch_status = result["status"]
    status_badge(f"ORCHESTRATION: {orch_status}", _status_type(orch_status))

    # -- Metrics row --
    st.markdown("<br>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        metric_card("Status", orch_status, f"Profile: {result['profile']}", _status_type(orch_status))
    with m2:
        metric_card("Proposals", str(result["planner"].get("proposal_count", 0)),
                     "Planner-generated", "normal")
    with m3:
        executed = sum(1 for r in result["records"] if r["status"] == "EXECUTED")
        metric_card("Executed", str(executed), "Proof-verified", "success")
    with m4:
        blocked = sum(1 for r in result["records"] if r["status"] in ("BLOCKED", "ERROR"))
        metric_card("Blocked", str(blocked), "Governance-enforced", "danger" if blocked else "normal")

    # -- Intent contract summary --
    st.markdown("<br>", unsafe_allow_html=True)
    section_title("INTENT CONTRACT")

    contract_data = result.get("contract", {})
    if contract_data:
        c1, c2 = st.columns(2)
        with c1:
            cyber_card(
                "Sealed Contract",
                f"""
                Session: {contract_data.get('session_id_short', '-')}<br>
                Intent Hash: {contract_data.get('intent_hash_short', '-')}<br>
                Sealed: {'✓ IMMUTABLE' if contract_data.get('sealed') else '✗'}<br>
                Allowed: {', '.join(contract_data.get('allowed_tools', [])) or 'none'}<br>
                Forbidden: {', '.join(contract_data.get('forbidden_tools', [])) or 'none'}
                """,
                min_height="180px",
            )
        with c2:
            planner_data = result.get("planner", {})
            cyber_card(
                "Planner Reasoning",
                f"""
                Task: {planner_data.get('task', '-')[:80]}<br><br>
                {planner_data.get('reasoning', '-')}<br><br>
                Proposals emitted: {planner_data.get('proposal_count', 0)}
                """,
                min_height="180px",
            )

    # -- Governance pipeline visualization --
    st.markdown("<br>", unsafe_allow_html=True)
    section_title("GOVERNANCE PIPELINE TRACE")

    has_records = len(result["records"]) > 0
    any_executed = any(r["status"] == "EXECUTED" for r in result["records"])
    any_blocked = any(r["status"] in ("BLOCKED", "ERROR") for r in result["records"])

    # Determine which stages passed
    cfi_pass = has_records  # if we got records, CFI was reached
    gate_pass = has_records and not any(
        "not allowed" in (r.get("error") or "").lower() or
        "forbidden" in (r.get("error") or "").lower()
        for r in result["records"]
    )
    proof_pass = any_executed  # proof succeeded if execution happened
    verify_pass = any_executed
    exec_pass = any_executed
    blocked_at_gate = has_records and not gate_pass
    blocked_at_proof = has_records and gate_pass and not proof_pass and not blocked_at_gate

    stages_html = "".join([
        _render_pipeline_stage("CONTRACT", True),
        _render_pipeline_stage("CFI", cfi_pass, blocked=False),
        _render_pipeline_stage("TOOL GATE", gate_pass, blocked=blocked_at_gate),
        _render_pipeline_stage("ZK PROOF", proof_pass, blocked=blocked_at_proof),
        _render_pipeline_stage("VERIFY", verify_pass, blocked=(has_records and not verify_pass and gate_pass and not blocked_at_proof)),
        _render_pipeline_stage("EXECUTE", exec_pass, blocked=any_blocked),
    ])

    st.markdown(f"""
<div class="pipeline-trace">
  {stages_html}
</div>
""", unsafe_allow_html=True)

    # -- Proposal outcome cards --
    st.markdown("<br>", unsafe_allow_html=True)
    section_title("PROPOSAL OUTCOMES")

    if result["records"]:
        for rec in result["records"]:
            _render_proposal_card(rec)
    else:
        cyber_card("No Proposals", "The planner did not generate any proposals for this prompt.", min_height="100px")

    # -- Execution outcome --
    if any_executed:
        section_title("EXECUTION RESULT")
        for rec in result["records"]:
            if rec["status"] == "EXECUTED" and rec.get("result_status"):
                cyber_card(
                    f"✓ {rec['tool_name']} — {rec['result_status']}",
                    f"""
                    Governance decision: <b style="color:#00FF88;">APPROVED</b><br>
                    Tool: {rec['tool_name']}<br>
                    Result status: {rec['result_status']}<br>
                    Result fields: {', '.join(rec.get('result_keys', []))}
                    """,
                    min_height="120px",
                )

    # -- Blocked alerts --
    if any_blocked:
        st.markdown("<br>", unsafe_allow_html=True)
        section_title("BLOCKED EXECUTION ALERTS")

        for rec in result["records"]:
            if rec["status"] in ("BLOCKED", "ERROR"):
                st.markdown(f"""
<div style="background:rgba(255,59,92,0.08);border:1px solid rgba(255,59,92,0.35);
border-radius:14px;padding:1.1rem;margin-bottom:0.75rem;">
  <div style="color:#FF3B5C;font-weight:700;font-size:1rem;margin-bottom:0.4rem;">
    🚨 GOVERNANCE BLOCK — {rec['tool_name']}
  </div>
  <div style="color:#E6F1FF;font-size:0.9rem;">
    Status: <b>{rec['status']}</b><br>
    Reason: {rec.get('error', 'Unknown governance violation')}
  </div>
</div>
""", unsafe_allow_html=True)

    # -- Audit trace reference --
    st.markdown("<br>", unsafe_allow_html=True)
    section_title("AUDIT TRACE")

    session_id = result.get("session_id")
    if session_id:
        all_logs = load_audit_logs()
        session_logs = [
            row for row in all_logs
            if row.get("session_id") == session_id
        ]

        if session_logs:
            st.caption(f"Showing {len(session_logs)} audit record(s) for session {session_id[:14]}...")

            trace_rows = [
                {
                    "timestamp": row.get("timestamp", "-"),
                    "tool": row.get("tool_name", "-"),
                    "status": row.get("status", "-"),
                    "action_hash": (row.get("action_hash", "") or "")[:14] + "...",
                    "verification": "✓" if row.get("verification") is True else "✗" if row.get("verification") is False else "-",
                    "execution_id": (row.get("execution_id", "") or "")[:14] + "..." if row.get("execution_id") else "-",
                }
                for row in session_logs
            ]

            st.dataframe(trace_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No audit records found for this session yet.")
    else:
        st.info("No session ID available — audit trace requires a completed pipeline run.")


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;color:#93A4C3;padding-bottom:2rem;font-size:0.9rem;">
    NIYAM-AI Governed Execution Console &nbsp;•&nbsp; Proof-Verified Intent Governance
</div>
""", unsafe_allow_html=True)
