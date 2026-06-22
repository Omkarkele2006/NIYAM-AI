"""
Centralized Plotly chart theme helpers for NIYAM-AI.

This module keeps dashboard charts visually consistent with the cyber
governance UI while staying lightweight and frontend-only.
"""

from __future__ import annotations

from typing import Any

import plotly.express as px
import plotly.graph_objects as go


PRIMARY_BG = "rgba(0,0,0,0)"
PLOT_BG = "rgba(17,20,27,0.40)"
TEXT_PRIMARY = "#E6E9EF"
TEXT_SECONDARY = "#9AA3B2"
GRID_COLOR = "rgba(31,36,48,0.80)"
AXIS_COLOR = "rgba(155,163,178,0.55)"

NEON_BLUE = "#22D3EE"
NEON_PURPLE = "#818CF8"
SUCCESS = "#10B981"
DANGER = "#F43F5E"
WARNING = "#F59E0B"
MUTED = "#4B5563"
CARD_BG = "rgba(17,20,27,0.95)"

CYBER_PALETTE = [
    NEON_BLUE,
    NEON_PURPLE,
    SUCCESS,
    WARNING,
    DANGER,
    "#60A5FA",
    "#34D399",
    "#A78BFA",
]

GOVERNANCE_STATUS_COLORS = {
    "EXECUTED":      SUCCESS,
    "SAFE":          SUCCESS,
    "VERIFIED":      SUCCESS,
    "COMPLETED":     SUCCESS,
    "BLOCKED":       DANGER,
    "FAILED":        DANGER,
    "REJECTED":      DANGER,
    "ERROR":         WARNING,
    "MISSING":       MUTED,
    "NOT_AVAILABLE": MUTED,
    "PROOF_PRESENT": NEON_BLUE,
    "PENDING":       WARNING,
    "UNKNOWN":       MUTED,
}


def status_color(status: str | None) -> str:
    """Return a standard governance color for a status label."""

    if not status:
        return MUTED

    return GOVERNANCE_STATUS_COLORS.get(str(status).upper(), MUTED)


def apply_cyber_theme(fig: go.Figure, *, height: int | None = None) -> go.Figure:
    """
    Apply NIYAM-AI's dark cyber dashboard style to a Plotly figure.

    The theme uses transparent backgrounds, restrained neon accents, readable
    typography, and subtle grid lines suitable for enterprise observability.
    """

    fig.update_layout(
        paper_bgcolor=PRIMARY_BG,
        plot_bgcolor=PLOT_BG,
        font={
            "family": "Inter, Arial, sans-serif",
            "color": TEXT_PRIMARY,
            "size": 13,
        },
        title={
            "font": {
                "color": TEXT_PRIMARY,
                "size": 17,
            },
            "x": 0.02,
            "xanchor": "left",
        },
        legend={
            "font": {"color": TEXT_SECONDARY},
            "bgcolor": "rgba(0,0,0,0)",
        },
        margin={"l": 24, "r": 24, "t": 56, "b": 36},
        hoverlabel={
            "bgcolor": CARD_BG,
            "bordercolor": NEON_BLUE,
            "font": {
                "family": "Inter, Arial, sans-serif",
                "color": TEXT_PRIMARY,
                "size": 12,
            },
        },
    )

    if height is not None:
        fig.update_layout(height=height)

    fig.update_xaxes(
        showgrid=True,
        gridcolor=GRID_COLOR,
        zeroline=False,
        linecolor=AXIS_COLOR,
        tickfont={"color": TEXT_SECONDARY},
        title_font={"color": TEXT_SECONDARY},
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=GRID_COLOR,
        zeroline=False,
        linecolor=AXIS_COLOR,
        tickfont={"color": TEXT_SECONDARY},
        title_font={"color": TEXT_SECONDARY},
    )

    return fig


def hover_template(*fields: str, extra: str = "<extra></extra>") -> str:
    """
    Build a consistent Plotly hover template from field names.

    Example:
        hover_template("tool_name", "count")
    """

    lines = [f"<b>{field}</b>: %{{customdata[{index}]}}" for index, field in enumerate(fields)]
    return "<br>".join(lines) + extra


def create_glow_bar_chart(
    data: list[dict[str, Any]],
    *,
    x: str,
    y: str,
    title: str,
    orientation: str = "v",
    color: str | None = None,
    labels: dict[str, str] | None = None,
    height: int = 360,
) -> go.Figure:
    """Create a cyber-styled bar chart for governance dashboards."""

    fig = px.bar(
        data,
        x=x,
        y=y,
        orientation=orientation,
        title=title,
        labels=labels,
        color=color,
        color_discrete_sequence=CYBER_PALETTE,
        color_continuous_scale=[NEON_BLUE, NEON_PURPLE, DANGER],
    )
    apply_cyber_theme(fig, height=height)
    fig.update_traces(
        marker_line_color="rgba(255,255,255,0.18)",
        marker_line_width=1,
        opacity=0.92,
        hovertemplate="%{x}<br>%{y}<extra></extra>",
    )
    return fig


def create_governance_pie_chart(
    data: list[dict[str, Any]],
    *,
    names: str,
    values: str,
    title: str,
    hole: float = 0.46,
    height: int = 360,
) -> go.Figure:
    """Create a cyber-styled donut chart for status distributions."""

    fig = px.pie(
        data,
        names=names,
        values=values,
        title=title,
        hole=hole,
        color=names,
        color_discrete_map=GOVERNANCE_STATUS_COLORS,
        color_discrete_sequence=CYBER_PALETTE,
    )
    apply_cyber_theme(fig, height=height)
    fig.update_traces(
        textfont={"color": TEXT_PRIMARY},
        marker={"line": {"color": "rgba(255,255,255,0.16)", "width": 1}},
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>",
    )
    return fig


def create_timeline_chart(
    data: list[dict[str, Any]],
    *,
    x: str,
    y: str,
    title: str,
    color: str | None = None,
    labels: dict[str, str] | None = None,
    height: int = 340,
) -> go.Figure:
    """Create a cyber-styled timeline chart for event activity."""

    fig = px.line(
        data,
        x=x,
        y=y,
        color=color,
        markers=True,
        title=title,
        labels=labels,
        color_discrete_map=GOVERNANCE_STATUS_COLORS,
        color_discrete_sequence=CYBER_PALETTE,
    )
    apply_cyber_theme(fig, height=height)
    fig.update_traces(
        line={"width": 2.5},
        marker={
            "size": 8,
            "line": {
                "width": 1,
                "color": "rgba(255,255,255,0.34)",
            },
        },
        hovertemplate="%{x}<br>Events: %{y}<extra></extra>",
    )
    return fig

