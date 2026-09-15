from __future__ import annotations

import streamlit as st

from streamlit_app.ui.theme import inject_global_css

st.set_page_config(
    page_title="CASE — Control Room",
    page_icon="\u2697\ufe0f",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()

PAGES = {
    "\U0001f3e0 Control Room": "control_room",
    "\u2696\ufe0f Triage": "triage",
    "\U0001f50d Case Explorer": "case_explorer",
    "\U0001f464 Human Review": "human_review",
    "\U0001f4cb Audit Trail": "audit_trail",
    "\U0001f52c Provider Lab": "provider_lab",
    "\U0001f4ca Evaluation Lab": "evaluation",
}

with st.sidebar:
    st.markdown("## CASE")
    st.caption("Case Assessment and Structured Evaluation")
    st.divider()
    selection = st.radio("Navigate", list(PAGES.keys()), label_visibility="collapsed")
    st.divider()
    api_url = st.text_input("API URL", value="http://localhost:8000", key="api_url_input")
    st.session_state["case_api_url"] = api_url

page = PAGES[selection]

if page == "control_room":
    from streamlit_app.views.control_room import render

    render()
elif page == "triage":
    from streamlit_app.views.triage import render

    render()
elif page == "case_explorer":
    from streamlit_app.views.case_explorer import render

    render()
elif page == "human_review":
    from streamlit_app.views.human_review import render

    render()
elif page == "audit_trail":
    from streamlit_app.views.audit_trail import render

    render()
elif page == "provider_lab":
    from streamlit_app.views.provider_lab import render

    render()
elif page == "evaluation":
    from streamlit_app.views.evaluation import render

    render()
