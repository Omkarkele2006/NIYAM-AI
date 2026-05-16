import streamlit as st


# =========================================================
# METRIC CARD
# =========================================================

def metric_card(title, value, delta="", status="normal"):

    glow_map = {
        "normal": "#00D1FF",
        "success": "#00FF88",
        "danger": "#FF3B5C",
        "warning": "#FFC857",
    }

    glow = glow_map.get(status, "#00D1FF")

    html = f"""
    <div style="
        background: rgba(18,26,43,0.82);
        border: 1px solid {glow};
        border-radius: 18px;
        padding: 1.4rem;
        min-height: 160px;
        backdrop-filter: blur(12px);
        box-shadow: 0 0 18px rgba(0,209,255,0.12);
    ">

        <div style="
            color:#93A4C3;
            font-size:0.9rem;
            margin-bottom:0.6rem;
        ">
            {title}
        </div>

        <div style="
            color:#E6F1FF;
            font-size:2rem;
            font-weight:700;
        ">
            {value}
        </div>

        <div style="
            color:#93A4C3;
            margin-top:0.7rem;
            font-size:0.82rem;
        ">
            {delta}
        </div>

    </div>
    """

    st.markdown(html, unsafe_allow_html=True)


# =========================================================
# CYBER CARD
# =========================================================

def cyber_card(title, content, min_height="280px"):

    html = f"""
    <div style="
        background: rgba(18,26,43,0.78);
        border:1px solid rgba(255,255,255,0.08);
        border-radius:20px;
        padding:1.6rem;
        min-height:{min_height};
        backdrop-filter: blur(14px);
        box-shadow: 0 4px 30px rgba(0,0,0,0.2);
    ">

        <h3 style="
            color:#00D1FF;
            font-family:Arial;
            letter-spacing:1px;
            margin-top:0;
        ">
            {title}
        </h3>

        <div style="
            color:#E6F1FF;
            line-height:1.8;
            font-size:0.95rem;
        ">
            {content}
        </div>

    </div>
    """

    st.markdown(html, unsafe_allow_html=True)


# =========================================================
# STATUS BADGE
# =========================================================

def status_badge(label, status="success"):

    color_map = {
        "success": "#00FF88",
        "danger": "#FF3B5C",
        "warning": "#FFC857",
        "info": "#00D1FF",
    }

    color = color_map.get(status, "#00D1FF")

    html = f"""
    <div style="
        display:inline-block;
        padding:0.35rem 0.9rem;
        border-radius:999px;
        border:1px solid {color};
        background: rgba(0,0,0,0.25);
        color:{color};
        font-size:0.8rem;
        font-weight:600;
        box-shadow: 0 0 10px rgba(0,209,255,0.15);
    ">
        ● {label}
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)