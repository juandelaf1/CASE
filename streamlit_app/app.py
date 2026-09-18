from __future__ import annotations

import sys
from pathlib import Path

_repo_root = str(Path(__file__).resolve().parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

import streamlit as st

from streamlit_app.ui.theme import inject_global_css

st.set_page_config(
    page_title="CASE — Centro de Decisiones IA",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()

PAGES_DEMO: dict[str, tuple[str, str]] = {
    "decision_center": ("nav_decision_center", "📋"),
    "triage": ("nav_triage", "⚗"),
    "comparison": ("nav_comparison", "⇄"),
    "human_review": ("nav_review", "⚖"),
    "audit_trail": ("nav_audit", "☰"),
}

PAGES_TECH: dict[str, tuple[str, str]] = {
    "cases": ("nav_cases", "☑"),
    "control_room": ("nav_control_room", "⚙"),
    "status": ("nav_status", "⚡"),
    "evaluation": ("nav_evaluation", "▲"),
    "counterfactual": ("nav_counterfactual", "☁"),
    "provider_lab": ("nav_provider_lab", "⚗"),
    "architecture": ("nav_architecture", "⌂"),
}

ALL_PAGES: dict[str, tuple[str, str]] = {}
ALL_PAGES.update(PAGES_DEMO)
ALL_PAGES.update(PAGES_TECH)

_BANNER_PATH = Path(_repo_root) / "docs" / "images" / "CASE_banner.jpg"


def _render_sidebar() -> None:
    from streamlit_app.i18n import t

    with st.sidebar:
        if _BANNER_PATH.exists():
            st.image(str(_BANNER_PATH), use_container_width=True)

        st.markdown(
            f'<div class="sidebar-brand">'
            f'<div class="sidebar-brand-name">CASE</div>'
            f'<div class="sidebar-brand-sub">{t("app_tagline")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.divider()

        lang = st.session_state.get("language", "es")
        lang_options = {"Español": "es", "English": "en"}
        selected_lang = st.selectbox(
            t("language_label"),
            options=list(lang_options.keys()),
            index=0 if lang == "es" else 1,
            key="_lang_selector",
            label_visibility="collapsed",
        )
        new_lang = lang_options[selected_lang]
        if new_lang != lang:
            st.session_state["language"] = new_lang
            st.rerun()

        st.divider()

        if "current_page" not in st.session_state:
            st.session_state["current_page"] = "decision_center"

        current = st.session_state["current_page"]

        # ── GROUP 1: OPERATION / DEMO ──
        st.markdown(
            f'<div class="sidebar-nav-section">{t("nav_demo_flow")}</div>',
            unsafe_allow_html=True,
        )
        for key in PAGES_DEMO:
            label_key, icon = ALL_PAGES[key]
            is_active = current == key
            if st.sidebar.button(
                f"{icon}  {t(label_key)}",
                key=f"nav_{key}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state["current_page"] = key
                st.rerun()

        st.divider()

        # ── GROUP 2: TECHNICAL / ENGINEERING (collapsed expander) ──
        with st.expander(t("nav_technical"), expanded=False):
            for key in PAGES_TECH:
                label_key, icon = ALL_PAGES[key]
                is_active = current == key
                if st.button(
                    f"{icon}  {t(label_key)}",
                    key=f"nav_{key}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                ):
                    st.session_state["current_page"] = key
                    st.rerun()

        st.divider()

        api_url = st.text_input(
            "API URL",
            value=st.session_state.get("case_api_url", "http://localhost:8000"),
            key="api_url_input",
            label_visibility="collapsed",
        )
        st.session_state["case_api_url"] = api_url


_render_sidebar()

page = st.session_state["current_page"]

if page == "decision_center":
    from streamlit_app.views.decision_center import render
    render()
elif page == "cases":
    from streamlit_app.views.case_explorer import render
    render()
elif page == "human_review":
    from streamlit_app.views.human_review import render
    render()
elif page == "audit_trail":
    from streamlit_app.views.audit_trail import render
    render()
elif page == "comparison":
    from streamlit_app.views.comparison import render
    render()
elif page == "provider_lab":
    from streamlit_app.views.provider_lab import render
    render()
elif page == "evaluation":
    from streamlit_app.views.evaluation import render
    render()
elif page == "counterfactual":
    from streamlit_app.views.counterfactual import render
    render()
elif page == "architecture":
    from streamlit_app.views.architecture import render
    render()
elif page == "control_room":
    from streamlit_app.views.control_room import render
    render()
elif page == "triage":
    from streamlit_app.views.triage import render
    render()
elif page == "status":
    from streamlit_app.views.status import render
    render()
