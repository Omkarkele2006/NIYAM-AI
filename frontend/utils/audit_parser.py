"""
Frontend-oriented audit helpers for NIYAM-AI.

This module adapts raw governance audit logs into small, reusable structures
that Streamlit pages can render as metrics, tables, and charts.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

import streamlit as st

from schema.governance_service import load_audit_logs


AuditRecord = dict[str, Any]


def _parse_timestamp(value: str | None) -> datetime | None:
    """Parse an audit timestamp into a timezone-aware UTC datetime."""

    if not value:
        return None

    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def _sort_by_timestamp(records: list[AuditRecord]) -> list[AuditRecord]:
    """Return records sorted by timestamp from newest to oldest."""

    return sorted(
        records,
        key=lambda row: _parse_timestamp(row.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )


@st.cache_data(ttl=10, show_spinner=False)
def get_latest_audit_logs(limit: int = 25) -> list[AuditRecord]:
    """Return the newest audit records for live tables and monitors."""

    logs = load_audit_logs(limit=limit)
    return _sort_by_timestamp(logs)


@st.cache_data(ttl=10, show_spinner=False)
def get_blocked_actions(limit: int | None = None) -> list[AuditRecord]:
    """Return blocked governance events, newest first."""

    logs = load_audit_logs(status="BLOCKED")
    sorted_logs = _sort_by_timestamp(logs)
    return sorted_logs[:limit] if limit is not None else sorted_logs


@st.cache_data(ttl=10, show_spinner=False)
def get_executed_actions(limit: int | None = None) -> list[AuditRecord]:
    """Return successfully executed governance events, newest first."""

    logs = load_audit_logs(status="EXECUTED")
    sorted_logs = _sort_by_timestamp(logs)
    return sorted_logs[:limit] if limit is not None else sorted_logs


@st.cache_data(ttl=10, show_spinner=False)
def get_verification_statistics() -> dict[str, int | float]:
    """Return proof verification counts and rate for dashboard cards."""

    logs = load_audit_logs()
    total    = len(logs)
    verified = sum(1 for row in logs if row.get("verification") is True)
    failed   = sum(1 for row in logs if row.get("verification") is False)
    missing  = total - verified - failed

    return {
        "total_records":     total,
        "verified":          verified,
        "failed":            failed,
        "missing":           missing,
        "verification_rate": round((verified / total) * 100, 2) if total else 0.0,
    }


@st.cache_data(ttl=10, show_spinner=False)
def get_session_statistics() -> dict[str, Any]:
    """Return session counts and latest session metadata."""

    logs = load_audit_logs()
    sessions = [row.get("session_id") for row in logs if row.get("session_id")]
    session_counts = Counter(sessions)
    latest = _sort_by_timestamp(logs)[0] if logs else None

    return {
        "unique_sessions":    len(session_counts),
        "latest_session_id":  latest.get("session_id")  if latest else None,
        "latest_intent_hash": latest.get("intent_hash") if latest else None,
        "session_counts":     dict(session_counts),
    }


@st.cache_data(ttl=10, show_spinner=False)
def get_tool_usage_frequency() -> list[dict[str, int | str]]:
    """Return tool usage counts in chart-friendly row format."""

    logs = load_audit_logs()
    counts = Counter(row.get("tool_name", "unknown") for row in logs)

    return [
        {"tool_name": tool_name, "count": count}
        for tool_name, count in counts.most_common()
    ]


@st.cache_data(ttl=30, show_spinner=False)
def get_recent_threat_activity(hours: int = 24, limit: int = 20) -> list[AuditRecord]:
    """Return recent blocked events for threat activity panels.

    TTL is 30 s — threat windows are measured in hours so a slightly longer
    cache is safe and avoids redundant timestamp comparisons on every render.
    """

    cutoff  = datetime.now(timezone.utc) - timedelta(hours=hours)
    blocked = get_blocked_actions()

    recent = [
        row
        for row in blocked
        if (_parse_timestamp(row.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc)) >= cutoff
    ]

    return recent[:limit]


@st.cache_data(ttl=10, show_spinner=False)
def get_audit_summary_metrics() -> dict[str, int | float | str | None]:
    """Return compact audit metrics suitable for Home and Live Monitor pages."""

    logs     = load_audit_logs()
    executed = [row for row in logs if row.get("status") == "EXECUTED"]
    blocked  = [row for row in logs if row.get("status") == "BLOCKED"]
    errors   = [row for row in logs if row.get("status") == "ERROR"]
    latest   = _sort_by_timestamp(logs)[0] if logs else None

    total         = len(logs)
    blocked_rate  = round((len(blocked)  / total) * 100, 2) if total else 0.0
    executed_rate = round((len(executed) / total) * 100, 2) if total else 0.0

    return {
        "total_actions":    total,
        "executed_actions": len(executed),
        "blocked_actions":  len(blocked),
        "error_actions":    len(errors),
        "blocked_rate":     blocked_rate,
        "executed_rate":    executed_rate,
        "latest_status":    latest.get("status")    if latest else None,
        "latest_tool":      latest.get("tool_name") if latest else None,
        "latest_timestamp": latest.get("timestamp") if latest else None,
    }
