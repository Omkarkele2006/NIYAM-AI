"""
NIYAM-AI — Enterprise UI Theme Helpers
Commit 12 Design System v12.0
"""

from pathlib import Path

import streamlit as st


# =========================
# DESIGN TOKENS (Python)
# =========================

BG_BASE        = "#0A0B0F"
BG_CARD        = "#11141B"
BG_ELEVATED    = "#181D27"

BORDER         = "#1F2430"

TEXT_PRIMARY   = "#E6E9EF"
TEXT_SECONDARY = "#9AA3B2"
TEXT_TERTIARY  = "#6B7280"

ACCENT         = "#22D3EE"
ACCENT_PURPLE  = "#818CF8"

SUCCESS        = "#10B981"
WARNING        = "#F59E0B"
DANGER         = "#F43F5E"
INFO           = "#60A5FA"
MUTED          = "#4B5563"

# Backward-compatible aliases (used in chart_theme.py and pages)
NEON_BLUE      = ACCENT
NEON_PURPLE    = ACCENT_PURPLE
PRIMARY_BG     = BG_BASE
SECONDARY_BG   = BG_CARD
CARD_BG        = BG_CARD


# =========================
# STATUS HELPERS
# =========================

STATUS_COLORS: dict[str, str] = {
    "EXECUTED":      SUCCESS,
    "SAFE":          SUCCESS,
    "VERIFIED":      SUCCESS,
    "COMPLETED":     SUCCESS,
    "BLOCKED":       DANGER,
    "FAILED":        DANGER,
    "REJECTED":      DANGER,
    "ERROR":         WARNING,
    "PENDING":       WARNING,
    "MISSING":       MUTED,
    "NOT_AVAILABLE": MUTED,
    "PROOF_PRESENT": ACCENT,
    "UNKNOWN":       MUTED,
}

BADGE_CLASS: dict[str, str] = {
    "success": "badge-success",
    "danger":  "badge-danger",
    "warning": "badge-warning",
    "info":    "badge-info",
    "accent":  "badge-accent",
    "purple":  "badge-purple",
    "muted":   "badge-muted",
    "normal":  "badge-muted",
}

def status_color(status: str | None) -> str:
    if not status:
        return MUTED
    return STATUS_COLORS.get(str(status).upper(), MUTED)


# =========================
# PAGE CONFIG
# =========================

def configure_page(title: str = "NIYAM-AI") -> None:
    st.set_page_config(
        page_title=title,
        page_icon="🛡",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    load_global_css()


# =========================
# GLOBAL CSS LOADER
# =========================

def load_global_css() -> None:
    css_path = (
        Path(__file__).resolve().parents[1]
        / "assets"
        / "css"
        / "cyber_theme.css"
    )
    with css_path.open("r", encoding="utf-8") as fh:
        css = fh.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# =========================
# PAGE HEADER
# =========================

def page_header(title: str, subtitle: str = "", badge_label: str = "", badge_kind: str = "accent") -> None:
    """Render a clean enterprise page header with optional inline badge."""

    badge_html = ""
    if badge_label:
        cls = BADGE_CLASS.get(badge_kind, "badge-accent")
        badge_html = f'<span class="badge {cls}"><span class="badge-dot"></span>{badge_label}</span>'

    st.markdown(
        f"""
        <div class="page-header">
            <div class="page-header-top">
                <h1 class="page-title">{title}</h1>
                {badge_html}
            </div>
            {"" if not subtitle else f'<p class="page-subtitle">{subtitle}</p>'}
        </div>
        """,
        unsafe_allow_html=True,
    )


# Backward-compatible alias used by many pages
def cyber_header(title: str, subtitle: str = "") -> None:
    page_header(title, subtitle)


# =========================
# SECTION TITLE / HEADER
# =========================

def section_title(text: str) -> None:
    """Render a compact uppercase section divider label."""
    st.markdown(
        f'<div class="section-title">{text}</div>',
        unsafe_allow_html=True,
    )


# Alias
def section_header(text: str) -> None:
    section_title(text)


# =========================
# BADGE
# =========================

def render_badge(label: str, kind: str = "accent") -> None:
    """Render an inline status badge."""
    cls = BADGE_CLASS.get(kind, "badge-accent")
    st.markdown(
        f'<span class="badge {cls}">{label}</span>',
        unsafe_allow_html=True,
    )


# Backward-compatible alias (was called status_badge in cards.py)
def status_badge_theme(label: str, kind: str = "accent") -> None:
    render_badge(label, kind)
