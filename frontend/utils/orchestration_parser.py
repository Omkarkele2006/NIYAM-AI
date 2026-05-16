"""
Frontend-oriented orchestration observability helpers for NIYAM-AI.

This module adapts raw governance audit logs into session-grouped, proposal-
aware structures that Streamlit pages can render as metrics, timelines, and
lifecycle visualisations.

Data source: schema.governance_service.load_audit_logs() only.

IMPORTANT — governance boundaries observed by this module:
- No imports from schema.orchestration (no planner, registry, or proposal objects)
- No direct file access (all data flows through governance_service)
- No execution capability (pure read-only transformation)
- Payload contents are never surfaced (stripped in _sanitize_record)
- ML feature vectors are never surfaced (stripped in _sanitize_record)
- All hash and session identifiers are pre-truncated for display safety
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from schema.governance_service import load_audit_logs


# ---------------------------------------------------------------------------
# Type aliases — mirrors audit_parser.py convention
# ---------------------------------------------------------------------------

AuditRecord = dict[str, Any]

# Number of characters shown for hashes and session IDs in display helpers.
# Matches the _short_value() length used across the existing frontend pages.
_HASH_PREVIEW_LEN: int = 14


# ---------------------------------------------------------------------------
# Private helpers — mirrors audit_parser.py private function style
# ---------------------------------------------------------------------------

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
    """Return records sorted by timestamp from oldest to newest."""

    return sorted(
        records,
        key=lambda row: _parse_timestamp(row.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc),
    )


def _truncate(value: str | None, length: int = _HASH_PREVIEW_LEN) -> str:
    """Return a safe, fixed-width preview of a hash or identifier string.

    Full values are never returned from this module so that pages cannot
    accidentally render unsanitised hash strings in editable or copyable
    fields without intentional action.
    """

    if not value or not isinstance(value, str):
        return "-"

    return value[:length] + "..." if len(value) > length else value


def _safe_str(value: Any) -> str:
    """Coerce a field value to a non-empty display string defensively."""

    if value is None:
        return "-"

    coerced = str(value).strip()
    return coerced if coerced else "-"


def _sanitize_record(row: AuditRecord) -> AuditRecord:
    """Return a display-safe copy of one audit record.

    Fields that must never reach the frontend are removed here:
      - payload   : may contain PII, financial parameters, or sensitive data
      - features  : raw ML circuit inputs — implementation detail only
      - log_hash  : full chain hash — not a display value
      - prev_hash : full chain hash — not a display value

    All remaining fields are returned as-is for downstream formatting.
    """

    return {
        key: value
        for key, value in row.items()
        if key not in {"payload", "features", "log_hash", "prev_hash"}
    }


def _status_of(row: AuditRecord) -> str:
    """Return a normalised status string from an audit record."""

    return _safe_str(row.get("status"))


def _session_of(row: AuditRecord) -> str | None:
    """Return the session_id from a record, or None when absent."""

    value = row.get("session_id")
    return value if isinstance(value, str) and value.strip() else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_orchestration_overview() -> dict[str, int | float | str | None]:
    """Return top-level orchestration metrics for dashboard summary cards.

    Mirrors get_audit_summary_metrics() in audit_parser.py — same structure,
    same rate calculation pattern, same None-safe latest-record handling.
    """

    logs = load_audit_logs()

    executed = [row for row in logs if _status_of(row) == "EXECUTED"]
    blocked  = [row for row in logs if _status_of(row) == "BLOCKED"]
    errors   = [row for row in logs if _status_of(row) == "ERROR"]

    unique_sessions = {
        _session_of(row)
        for row in logs
        if _session_of(row) is not None
    }

    total = len(logs)
    blocked_rate  = round((len(blocked)  / total) * 100, 2) if total else 0.0
    executed_rate = round((len(executed) / total) * 100, 2) if total else 0.0

    # Most recently logged proposal (newest last in JSONL)
    latest = logs[-1] if logs else None

    return {
        "total_proposals":   total,
        "executed_proposals": len(executed),
        "blocked_proposals":  len(blocked),
        "error_proposals":    len(errors),
        "unique_sessions":    len(unique_sessions),
        "blocked_rate":       blocked_rate,
        "executed_rate":      executed_rate,
        "latest_status":      latest.get("status")    if latest else None,
        "latest_tool":        latest.get("tool_name") if latest else None,
        "latest_timestamp":   latest.get("timestamp") if latest else None,
        "latest_session":     _truncate(_session_of(latest)) if latest else None,
    }


def get_session_list() -> list[dict[str, Any]]:
    """Return one summary row per unique orchestration session, newest first.

    Each row contains display-safe, pre-truncated identifiers and aggregate
    counts computed from the audit log.  No payload or feature data is
    included.

    Return shape per row:
        session_label   : truncated session_id for display
        session_id      : truncated session_id (same — never full value)
        intent_label    : truncated intent_hash for display
        total_proposals : count of log entries for this session
        executed        : count of EXECUTED entries
        blocked         : count of BLOCKED entries
        errors          : count of ERROR entries
        first_seen      : earliest timestamp string for the session
        last_seen       : latest timestamp string for the session
        governance_rate : percentage of proposals that were executed
    """

    logs = load_audit_logs()

    # Group records by session_id, ignoring records with no session
    session_map: dict[str, list[AuditRecord]] = defaultdict(list)
    for row in logs:
        sid = _session_of(row)
        if sid is not None:
            session_map[sid].append(row)

    if not session_map:
        return []

    rows: list[dict[str, Any]] = []

    for sid, records in session_map.items():
        sorted_records = _sort_by_timestamp(records)

        executed = sum(1 for r in records if _status_of(r) == "EXECUTED")
        blocked  = sum(1 for r in records if _status_of(r) == "BLOCKED")
        errors   = sum(1 for r in records if _status_of(r) == "ERROR")
        total    = len(records)

        first_ts = sorted_records[0].get("timestamp")  if sorted_records else None
        last_ts  = sorted_records[-1].get("timestamp") if sorted_records else None

        # Intent hash is expected to be consistent within a session; take the
        # first non-null occurrence defensively.
        intent_hash = next(
            (r.get("intent_hash") for r in records if r.get("intent_hash")),
            None,
        )

        governance_rate = round((executed / total) * 100, 2) if total else 0.0

        rows.append({
            "session_label":    _truncate(sid),
            "session_id":       _truncate(sid),
            "intent_label":     _truncate(intent_hash),
            "total_proposals":  total,
            "executed":         executed,
            "blocked":          blocked,
            "errors":           errors,
            "first_seen":       _safe_str(first_ts),
            "last_seen":        _safe_str(last_ts),
            "governance_rate":  governance_rate,
        })

    # Sort sessions newest-first by their last observed timestamp
    rows.sort(
        key=lambda r: r["last_seen"],
        reverse=True,
    )

    return rows


def get_session_proposals(session_id: str) -> list[dict[str, Any]]:
    """Return display-safe proposal event rows for one orchestration session.

    Rows are ordered oldest-first so pages can render a chronological
    proposal stream matching the lifecycle flow (PROPOSED → outcome).

    Payload and feature data are stripped.  Hashes are truncated.

    Return shape per row:
        timestamp       : raw ISO timestamp string (for display formatting)
        tool            : tool_name or "-"
        status          : EXECUTED / BLOCKED / ERROR / "-"
        verification    : "VERIFIED" / "FAILED" / "NOT_AVAILABLE"
        action_hash     : truncated action_hash
        intent_hash     : truncated intent_hash
        reason          : block reason or "-"
    """

    logs = load_audit_logs()

    session_records = [
        row for row in logs
        if _session_of(row) == session_id
    ]

    if not session_records:
        return []

    ordered = _sort_by_timestamp(session_records)

    result: list[dict[str, Any]] = []

    for row in ordered:
        verification_raw = row.get("verification")
        if verification_raw is True:
            verification_label = "VERIFIED"
        elif verification_raw is False:
            verification_label = "FAILED"
        else:
            verification_label = "NOT_AVAILABLE"

        result.append({
            "timestamp":    _safe_str(row.get("timestamp")),
            "tool":         _safe_str(row.get("tool_name")),
            "status":       _safe_str(row.get("status")),
            "verification": verification_label,
            "action_hash":  _truncate(row.get("action_hash")),
            "intent_hash":  _truncate(row.get("intent_hash")),
            "reason":       _safe_str(row.get("reason")),
        })

    return result


def get_proposal_status_distribution() -> list[dict[str, Any]]:
    """Return proposal counts by status for donut and bar chart rendering.

    Return shape:
        [{"status": "EXECUTED", "count": N}, {"status": "BLOCKED", "count": N}, ...]

    Unknown statuses are grouped under "OTHER" so charts remain clean even
    if the audit log contains unexpected status strings from future versions.
    """

    logs = load_audit_logs()

    known_statuses = {"EXECUTED", "BLOCKED", "ERROR"}
    counts: Counter[str] = Counter()

    for row in logs:
        status = _status_of(row)
        bucket = status if status in known_statuses else "OTHER"
        counts[bucket] += 1

    # Return in a deterministic display order
    display_order = ["EXECUTED", "BLOCKED", "ERROR", "OTHER"]

    return [
        {"status": s, "count": counts.get(s, 0)}
        for s in display_order
        if counts.get(s, 0) > 0
    ]


def get_blocked_proposal_analytics() -> dict[str, Any]:
    """Return structured analytics for blocked proposal panels.

    Derives block-reason distributions, most-targeted tools, block rate, and
    latest block timestamp exclusively from audit log records with status
    BLOCKED.

    Return shape:
        reason_distribution : list[{"reason": str, "count": int}]
        tool_distribution   : list[{"tool_name": str, "count": int}]
        total_blocked       : int
        most_common_reason  : str or None
        most_blocked_tool   : str or None
        latest_block_ts     : str or None  (ISO timestamp of most recent block)
        block_rate          : float        (percent of all proposals that were blocked)
    """

    all_logs = load_audit_logs()
    blocked  = [row for row in all_logs if _status_of(row) == "BLOCKED"]

    total_all    = len(all_logs)
    total_blocked = len(blocked)
    block_rate   = round((total_blocked / total_all) * 100, 2) if total_all else 0.0

    reason_counts: Counter[str] = Counter()
    tool_counts:   Counter[str] = Counter()

    for row in blocked:
        reason = row.get("reason")
        reason_counts[_safe_str(reason)] += 1

        tool = row.get("tool_name")
        tool_counts[_safe_str(tool)] += 1

    # Most recent block — blocked records are already in JSONL order; find max
    sorted_blocked = _sort_by_timestamp(blocked)
    latest_block = sorted_blocked[-1] if sorted_blocked else None

    most_common_reason = reason_counts.most_common(1)[0][0] if reason_counts else None
    most_blocked_tool  = tool_counts.most_common(1)[0][0]   if tool_counts  else None

    return {
        "reason_distribution": [
            {"reason": reason, "count": count}
            for reason, count in reason_counts.most_common()
        ],
        "tool_distribution": [
            {"tool_name": tool, "count": count}
            for tool, count in tool_counts.most_common()
        ],
        "total_blocked":     total_blocked,
        "most_common_reason": most_common_reason,
        "most_blocked_tool":  most_blocked_tool,
        "latest_block_ts":    latest_block.get("timestamp") if latest_block else None,
        "block_rate":         block_rate,
    }


def get_orchestration_timeline() -> list[dict[str, Any]]:
    """Return minute-bucketed event counts for orchestration timeline charts.

    Each row represents one (minute_bucket, status) combination with an event
    count.  This is the same bucketing pattern used in 4_Audit_Logs.py and
    3_Proof_Explorer.py for timeline line charts.

    Return shape:
        [{"minute": "2024-01-01 12:34", "status": "EXECUTED", "events": N}, ...]

    Records with unparseable timestamps are silently skipped — matching the
    defensive pattern in the existing timeline renderers.
    """

    logs = load_audit_logs()

    bucket_counts: Counter[tuple[str, str]] = Counter()

    for row in logs:
        ts = _parse_timestamp(row.get("timestamp"))
        if ts is None:
            continue

        minute_bucket = ts.strftime("%Y-%m-%d %H:%M")
        status = _status_of(row)
        bucket_counts[(minute_bucket, status)] += 1

    return [
        {"minute": minute, "status": status, "events": count}
        for (minute, status), count in sorted(bucket_counts.items())
    ]


def get_intent_hash_groups() -> list[dict[str, Any]]:
    """Return proposal counts grouped by intent_hash (governance contract).

    Each intent_hash represents one sealed IntentContract.  Grouping by it
    shows how many proposals were evaluated under each governance policy.

    Return shape per row:
        intent_label    : truncated intent_hash for display
        total_proposals : int
        executed        : int
        blocked         : int
        session_count   : int  (number of distinct sessions under this contract)
        governance_rate : float (executed / total * 100)
    """

    logs = load_audit_logs()

    # Group by intent_hash; skip records with no intent_hash
    intent_map: dict[str, list[AuditRecord]] = defaultdict(list)
    for row in logs:
        ih = row.get("intent_hash")
        if isinstance(ih, str) and ih.strip():
            intent_map[ih].append(row)

    if not intent_map:
        return []

    rows: list[dict[str, Any]] = []

    for intent_hash, records in intent_map.items():
        executed = sum(1 for r in records if _status_of(r) == "EXECUTED")
        blocked  = sum(1 for r in records if _status_of(r) == "BLOCKED")
        total    = len(records)

        # Count distinct sessions that operated under this contract
        sessions_under = {
            _session_of(r)
            for r in records
            if _session_of(r) is not None
        }

        governance_rate = round((executed / total) * 100, 2) if total else 0.0

        rows.append({
            "intent_label":    _truncate(intent_hash),
            "total_proposals": total,
            "executed":        executed,
            "blocked":         blocked,
            "session_count":   len(sessions_under),
            "governance_rate": governance_rate,
        })

    # Sort by total proposals descending — most active contracts first
    rows.sort(key=lambda r: r["total_proposals"], reverse=True)

    return rows
