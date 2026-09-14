from __future__ import annotations

import streamlit as st

from streamlit_app.views import evaluation, status, triage
from streamlit_app.components.hitl import hitl_list

st.set_page_config(
    page_title="CASE — Decision Center",
    page_icon="⚖️",
    layout="wide",
)

st.title("CASE — Decision Center")
st.markdown("*AI-assisted operational case triage*")

tab1, tab2, tab3 = st.tabs(["Decision Center", "Provider Evaluation", "System Status"])

with tab1:
    triage.render()
    hitl_list()

with tab2:
    evaluation.render()

with tab3:
    status.render()
