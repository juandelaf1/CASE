import streamlit as st

from streamlit_app.client import CASEClient


def get_client() -> CASEClient:
    if "case_client" not in st.session_state:
        st.session_state.case_client = CASEClient()
    return st.session_state.case_client
