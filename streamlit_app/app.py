from __future__ import annotations

import sys
from pathlib import Path

_repo_root = str(Path(__file__).resolve().parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

import streamlit as st

from streamlit_app.ui.theme import inject_global_css

st.set_page_config(
    page_title="CASE \u2014 AI Decision Center",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()

PAGES = {
    "main": {
        "decision_center": ("nav_decision_center", "\u2b21"),
        "cases": ("nav_cases", "\u2611"),
        "human_review": ("nav_review", "\u2696"),
        "audit_trail": ("nav_audit", "\u2630"),
        "comparison": ("nav_comparison", "\u21c4"),
    },
    "labs": {
        "provider_lab": ("nav_provider_lab", "\u2697"),
        "evaluation": ("nav_evaluation", "\u25b2"),
        "counterfactual": ("nav_counterfactual", "\u2601"),
        "architecture": ("nav_architecture", "\u2302"),
    },
}

ALL_PAGES: dict[str, tuple[str, str]] = {}
for section_pages in PAGES.values():
    ALL_PAGES.update(section_pages)

# Banner asset path (relative to repo root)
_BANNER_PATH = Path(_repo_root) / "docs" / "images" / "CASE_banner.jpg"


def _render_sidebar() -> None:
    from streamlit_app.i18n import t

    with st.sidebar:
        # Logo
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

        # Language selector
        lang = st.session_state.get("language", "es")
        lang_options = {"Espa\u00f1ol": "es", "English": "en"}
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

        st.markdown(f'<div class="sidebar-nav-section">{t("nav_decision_flow")}</div>', unsafe_allow_html=True)
        for key in PAGES["main"]:
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
        st.markdown(f'<div class="sidebar-nav-section">{t("nav_labs")}</div>', unsafe_allow_html=True)
        for key in PAGES["labs"]:
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
