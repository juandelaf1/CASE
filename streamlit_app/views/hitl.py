"""HITL (Human-in-the-loop) views for the CASE platform."""

import streamlit as st
from streamlit_app.components.hitl import hitl_detail as _hitl_detail, hitl_list as _hitl_list


def hitl_list() -> None:
    """Show pending HITL decisions for review."""
    decisions = _hitl_list()
    if not decisions:
        st.info("No pending HITL decisions.")
        return

    st.subheader("Pending HITL Decisions")
    for decision in decisions:
        _hitl_detail(decision.get("decision_id", ""))


def hitl_view(hitl_list_visible: bool = True) -> None:
    """Main HITL view component."""
    if hitl_list_visible:
        hitl_list()
    else:
        st.info("All decisions view not yet implemented.")