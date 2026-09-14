import streamlit as st

from streamlit_app.views import evaluation, status, triage
from streamlit_app.components.hitl import hitl_list

st.set_page_config(
    page_title="CASE — AI Decision Platform",
    page_icon="⚖️",
    layout="wide",
)

st.title("CASE — AI Decision Platform")
st.markdown("*Domain-agnostic decision assistance*")

tab1, tab2, tab3 = st.tabs(["Decision Center", "Provider Evaluation", "System Status"])

with tab1:
    triage.render()
    hitl_list()

with tab2:
    evaluation.render()

with tab3:
    status.render()
