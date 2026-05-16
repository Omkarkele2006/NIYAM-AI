import streamlit as st


# =========================
# COLOR PALETTE
# =========================

PRIMARY_BG = "#0B1020"
SECONDARY_BG = "#121A2B"

CARD_BG = "rgba(18, 26, 43, 0.75)"

NEON_BLUE = "#00D1FF"
NEON_PURPLE = "#9D4EDD"

SUCCESS = "#00FF88"
DANGER = "#FF3B5C"
WARNING = "#FFC857"

TEXT_PRIMARY = "#E6F1FF"
TEXT_SECONDARY = "#93A4C3"

BORDER = "rgba(255,255,255,0.08)"


# =========================
# PAGE CONFIG
# =========================

def configure_page(title="NIYAM-AI"):

    st.set_page_config(
        page_title=title,
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="collapsed"
    )


# =========================
# GLOBAL CSS LOADER
# =========================

def load_global_css():

    with open("frontend/assets/css/cyber_theme.css") as f:
        css = f.read()

    st.markdown(
        f"<style>{css}</style>",
        unsafe_allow_html=True
    )


# =========================
# CYBER HEADER
# =========================

def cyber_header(title, subtitle=""):

    st.markdown(
        f"""
        <div class="hero-container">
            <h1 class="hero-title">{title}</h1>
            <p class="hero-subtitle">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================
# SECTION TITLE
# =========================

def section_title(text):

    st.markdown(
        f"""
        <div class="section-title">
            {text}
        </div>
        """,
        unsafe_allow_html=True
    )