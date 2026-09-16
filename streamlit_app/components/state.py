from __future__ import annotations

import streamlit as st

from streamlit_app.client import CASEClient


def get_client() -> CASEClient:
    api_url = st.session_state.get("case_api_url", "http://localhost:8000")
    if "case_client" not in st.session_state or st.session_state.get("case_client_base_url") != api_url:
        st.session_state.case_client = CASEClient(base_url=api_url)
        st.session_state.case_client_base_url = api_url
    return st.session_state.case_client
