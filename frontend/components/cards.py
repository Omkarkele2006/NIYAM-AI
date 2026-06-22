"""
NIYAM-AI — Enterprise UI Components
Commit 12 Design System v12.0

All components render via CSS classes defined in cyber_theme.css.
Python-side inline styles are used only for dynamic values (e.g. status colors).
"""

from textwrap import dedent

import streamlit as st

from utils.theme import (
    TEXT_PRIMARY,
)


# =========================
# BADGE CLASS MAP
# =========================

_BADGE_KIND_MAP: dict[str, str] = {
    "success": "badge-success",
    "danger":  "badge-danger",
    "warning": "badge-warning",
    "info":    "badge-info",
    "accent":  "badge-accent",
    "purple":  "badge-purple",
    "normal":  "badge-muted",
    "muted":   "badge-muted",
}

_KPI_ACCENT_MAP: dict[str, str] = {
    "success": "success",
    "danger":  "danger",
    "warning": "warning",
    "info":    "info",
    "accent":  "accent",
    "purple":  "purple",
    "normal":  "muted",
    "muted":   "muted",
}


# =========================
# STATUS BADGE
# =========================

def status_badge(label: str, status: str = "success") -> None:
    """Render an inline pill badge. status maps to a badge-* CSS class."""
    cls = _BADGE_KIND_MAP.get(status, "badge-muted")
    st.markdown(
        f'<span class="badge {cls}">{label}</span>',
        unsafe_allow_html=True,
    )


# =========================
# METRIC CARD  (KPI card)
# =========================

def metric_card(
    title: str,
    value: str,
    delta: str = "",
    status: str = "normal",
) -> None:
    """
    Render a compact KPI metric card.

    The card uses a coloured left-border accent (the enterprise equivalent of a
    neon glow) to communicate status at a glance without being noisy.
    """
    accent_cls = _KPI_ACCENT_MAP.get(status, "muted")

    html = f"""
<div class="kpi-card {accent_cls}">
  <div class="kpi-label">{title}</div>
  <div class="kpi-value">{value}</div>
  {"" if not delta else f'<div class="kpi-delta">{delta}</div>'}
</div>
"""
    st.markdown(html, unsafe_allow_html=True)


# =========================
# CYBER CARD  (panel)
# =========================

def cyber_card(title: str, content: str, min_height: str = "280px") -> None:
    """
    Render a dark panel card.

    Content may include HTML tags (e.g. <b>, <br>).
    The min_height is applied as an inline style because it is
    caller-controlled and cannot be expressed as a static CSS class.
    """
    clean_content = "\n".join(
        line.strip()
        for line in dedent(content).strip().splitlines()
    )

    html = f"""
<div class="panel" style="min-height:{min_height};">
  <div class="panel-title">{title}</div>
  <div style="color:{TEXT_PRIMARY};line-height:1.75;font-size:0.9rem;">
    {clean_content}
  </div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)


# =========================
# ALERT CARD
# =========================

def alert_card(message: str, level: str = "info") -> None:
    """
    Render an inline alert banner.
    level: 'success' | 'danger' | 'warning' | 'info'
    """
    icon_map = {
        "success": "✓",
        "danger":  "⚠",
        "warning": "⚡",
        "info":    "ℹ",
    }
    icon = icon_map.get(level, "ℹ")
    cls = f"alert-card {level}"

    html = f"""
<div class="{cls}">
  <span style="flex-shrink:0;font-size:0.95rem;">{icon}</span>
  <span style="line-height:1.5;">{message}</span>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)
