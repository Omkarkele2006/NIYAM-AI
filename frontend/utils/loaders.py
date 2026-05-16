import json
from pathlib import Path

import streamlit as st


# =========================================================
# BASE PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ASSETS_DIR = BASE_DIR / "assets"

LOTTIE_DIR = ASSETS_DIR / "lottie"
IMAGES_DIR = ASSETS_DIR / "images"


# =========================================================
# GENERIC JSON LOADER
# =========================================================

@st.cache_data(show_spinner=False)
def load_json(filepath):

    """
    Load any JSON file safely.
    """

    path = Path(filepath)

    if not path.exists():
        return None

    try:

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:

        return {
            "error": str(e)
        }


# =========================================================
# LOTTIE LOADER
# =========================================================

@st.cache_data(show_spinner=False)
def load_lottie(filename):

    """
    Load lottie animation from assets/lottie
    """

    filepath = LOTTIE_DIR / filename

    return load_json(filepath)


# =========================================================
# SAFE TEXT FILE LOADER
# =========================================================

@st.cache_data(show_spinner=False)
def load_text(filepath):

    """
    Load text-based files safely.
    """

    path = Path(filepath)

    if not path.exists():
        return None

    try:

        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    except Exception as e:

        return f"ERROR: {str(e)}"


# =========================================================
# SAFE IMAGE PATH
# =========================================================

def image_path(filename):

    """
    Return image path safely.
    """

    return str(IMAGES_DIR / filename)