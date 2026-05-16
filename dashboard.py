# dashboard.py

import streamlit as st
import pandas as pd
import json
import os
import subprocess
from datetime import datetime
import plotly.express as px

LOG_FILE = "audit_log.jsonl"

st.set_page_config(page_title="Niyam-AI Trust Dashboard", layout="wide")

st.title("Niyam-AI Trust Dashboard")
st.caption("Cryptographically Verified AI Governance System")

# ------------------------
# RUN TEST BUTTON
# ------------------------
colA, colB = st.columns([1,3])

with colA:
    if st.button("Run Demo Simulation"):
        subprocess.run(["python", "test_phase2.py"])
        st.success("Simulation Executed")
        st.rerun()

with colB:
    if os.path.exists(LOG_FILE):
        st.caption(f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")

# ------------------------
# LOAD LOGS
# ------------------------
if not os.path.exists(LOG_FILE):
    st.warning("No logs found. Run simulation first.")
    st.stop()

data = []
with open(LOG_FILE, "r") as f:
    for line in f:
        data.append(json.loads(line))

df = pd.DataFrame(data)

# ------------------------
# METRICS
# ------------------------
col1, col2, col3 = st.columns(3)

total_actions = len(df)
safe_count = len(df[df["status"] == "SAFE"])
blocked_count = len(df[df["status"] == "BLOCKED"])

col1.metric("Total Actions", total_actions)
col2.metric("Safe Actions", safe_count)
col3.metric("Blocked Actions", blocked_count)

st.divider()

# ------------------------
# SESSION INFO
# ------------------------
latest_session = df["session_id"].iloc[-1]
latest_intent = df["intent_hash"].iloc[-1]

st.subheader("Current Session")
st.code(f"Session ID: {latest_session}")
st.code(f"IntentHash: {latest_intent}")

st.divider()

# ------------------------
# INTERACTIVE PIE CHART
# ------------------------
st.subheader("Safe vs Blocked Distribution")

status_counts = df["status"].value_counts().reset_index()
status_counts.columns = ["Status", "Count"]

fig_pie = px.pie(
    status_counts,
    names="Status",
    values="Count",
    title="Safe vs Blocked",
    hole=0.4
)

st.plotly_chart(fig_pie, use_container_width=True)

st.divider()

# ------------------------
# INTERACTIVE TOOL USAGE
# ------------------------
st.subheader("Tool Usage Frequency")

tool_counts = df["tool_name"].value_counts().reset_index()
tool_counts.columns = ["Tool", "Count"]

fig_bar = px.bar(
    tool_counts,
    x="Count",
    y="Tool",
    orientation="h",
    title="Tool Usage",
)

st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# ------------------------
# LOG TABLE
# ------------------------
st.subheader("Audit Log Records")
st.dataframe(
    df.sort_values("timestamp", ascending=False),
    use_container_width=True
)

# ------------------------
# FOOTER
# ------------------------
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; font-size: 14px;'>
    © 2026 <b>Niyam-AI v1.0</b><br>
    Intent-Bound AI with Cryptographic Guardrails<br>
    Developed by SY F-18 | VIT Pune
    </div>
    """,
    unsafe_allow_html=True
)