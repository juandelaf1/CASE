from __future__ import annotations

import streamlit as st

from streamlit_app.components.state import get_client


def render() -> None:
    st.header("System Status")
    client = get_client()

    try:
        health = client.health_sync()
        st.success(f"API: {health.get('status', 'unknown')}")
        st.markdown(f"**Version:** {health.get('version', 'N/A')}")
    except Exception:
        st.error("Cannot connect to CASE API.")
        return

    try:
        domains = client.list_domains_sync()
        if domains:
            st.markdown("**Registered Domains:**")
            for d in domains:
                st.markdown(f"- `{d}`")
    except Exception:
        pass
