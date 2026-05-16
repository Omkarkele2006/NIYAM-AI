from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


FRONTEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = FRONTEND_ROOT.parent

for path in (REPO_ROOT, FRONTEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from components.cards import cyber_card, metric_card, status_badge
from utils.theme import configure_page, load_global_css, section_title


configure_page("Contact | NIYAM-AI")
load_global_css()

section_title("CONTACT NIYAM-AI")
status_badge("OFFICIAL PROJECT CONTACT", "info")

top_col1, top_col2, top_col3, top_col4 = st.columns(4)

with top_col1:
    metric_card("Platform", "NIYAM-AI", "Verifiable governance", "normal")

with top_col2:
    metric_card("Institution", "VIT Pune", "Computer Engineering", "success")

with top_col3:
    metric_card("Cohort", "SY CS F18", "EDI project team", "warning")

with top_col4:
    metric_card("Focus", "AI Safety", "zkML governance", "danger")

st.markdown("<br>", unsafe_allow_html=True)

section_title("CONTACT OVERVIEW")

overview_col1, overview_col2 = st.columns([1.35, 1])

with overview_col1:
    cyber_card(
        "Intent-Bound Verifiable AI Governance System",
        """
        NIYAM-AI is a Verifiable AI Governance Platform developed at
        Vishwakarma Institute of Technology, Pune. The project focuses on
        governing autonomous AI execution through intent contracts,
        cryptographic verification, zkML proof generation, and immutable audit
        observability.
        """,
        min_height="260px",
    )

with overview_col2:
    cyber_card(
        "Collaboration Message",
        """
        We welcome technical discussion, research feedback, academic evaluation,
        and collaboration around AI governance, verifiable execution, zkML
        security, and enterprise-grade AI safety systems.
        """,
        min_height="260px",
    )

section_title("TEAM DIRECTORY")

team_col1, team_col2 = st.columns(2)

with team_col1:
    cyber_card(
        "Om Karkele",
        """
        Role: Full Stack Architecture<br>
        Contribution Area: Governance Engine Integration, Frontend Observability,
        architecture coordination, and system-level integration.
        """,
        min_height="250px",
    )

with team_col2:
    cyber_card(
        "Aditya Katkar",
        """
        Role: zkML Pipeline<br>
        Contribution Area: Proof Verification, Security Logic, zkML workflow,
        and cryptographic verification support.
        """,
        min_height="250px",
    )

team_col3, team_col4 = st.columns(2)

with team_col3:
    cyber_card(
        "Yash Kashid",
        """
        Role: Audit Analytics<br>
        Contribution Area: Threat Monitoring, Visualization, audit metrics, and
        governance analytics dashboarding.
        """,
        min_height="250px",
    )

with team_col4:
    cyber_card(
        "Kartik Mandhane",
        """
        Role: UI Engineering<br>
        Contribution Area: Streamlit Components, System Integration, interface
        consistency, and cyber governance presentation design.
        """,
        min_height="250px",
    )

section_title("GUIDE AND MENTOR")

guide_col1, guide_col2 = st.columns([1, 1])

with guide_col1:
    cyber_card(
        "Prof. Manisha More",
        """
        Assistant Professor<br>
        Vishwakarma Institute of Technology, Pune<br><br>
        Academic guide and mentor for the NIYAM-AI project.
        """,
        min_height="230px",
    )

with guide_col2:
    cyber_card(
        "Project Mentorship",
        """
        Guidance focuses on secure system design, research relevance, technical
        rigor, project presentation, and practical engineering for EDI
        evaluation.
        """,
        min_height="230px",
    )

section_title("COMMUNICATION CHANNELS")

channel_col1, channel_col2, channel_col3 = st.columns(3)

with channel_col1:
    cyber_card(
        "Email",
        """
        Primary Contact<br><br>
        <a href="mailto:omavkarkele@gmail.com" style="color:#00D1FF;">
        omavkarkele@gmail.com
        </a>
        """,
        min_height="230px",
    )

with channel_col2:
    cyber_card(
        "GitHub Repository",
        """
        Source Code and Project Repository<br><br>
        <a href="https://github.com/Omkarkele2006/NIYAM-AI" target="_blank" style="color:#00D1FF;">
        github.com/Omkarkele2006/NIYAM-AI
        </a>
        """,
        min_height="230px",
    )

with channel_col3:
    cyber_card(
        "Institution",
        """
        Vishwakarma Institute of Technology (VIT), Pune<br>
        Computer Engineering Department<br>
        SY CS F18
        """,
        min_height="230px",
    )

section_title("RESEARCH AND COLLABORATION")

research_col1, research_col2 = st.columns([1, 1])

with research_col1:
    cyber_card(
        "Research Interests",
        """
        AI governance research<br>
        zkML exploration<br>
        Cryptographic execution verification<br>
        Enterprise AI safety<br>
        Trustworthy autonomous systems
        """,
        min_height="260px",
    )

with research_col2:
    cyber_card(
        "Collaboration Areas",
        """
        Academic collaboration<br>
        Technical demos and architecture walkthroughs<br>
        Enterprise governance discussions<br>
        Verifiable AI safety prototypes<br>
        zkML proof-system experimentation
        """,
        min_height="260px",
    )

section_title("OFFICIAL PROJECT FOOTER")

cyber_card(
    "NIYAM-AI",
    """
    Intent-Bound Verifiable AI Governance System<br><br>
    Developed at Vishwakarma Institute of Technology, Pune<br>
    Computer Engineering Department | SY CS F18
    """,
    min_height="180px",
)
