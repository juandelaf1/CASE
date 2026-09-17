from __future__ import annotations

import streamlit as st

from streamlit_app.i18n import t
from streamlit_app.ui.components import render_metric_cards

CONNECTED_COMPONENTS = [
    {"name": "Contracts", "layer": "Foundation", "status": "CONNECTED", "description": "Pydantic v2 models at all public boundaries"},
    {"name": "LLMProvider", "layer": "Ports", "status": "CONNECTED", "description": "Provider-agnostic LLM abstraction"},
    {"name": "DomainRegistry", "layer": "Domain", "status": "CONNECTED", "description": "Domain policy registration and resolution"},
    {"name": "UrbanPolicy", "layer": "Domain", "status": "CONNECTED", "description": "Urban operations domain policy"},
    {"name": "LogisticsPolicy", "layer": "Domain", "status": "CONNECTED", "description": "Logistics domain policy"},
    {"name": "InfrastructurePolicy", "layer": "Domain", "status": "CONNECTED", "description": "Infrastructure domain policy"},
    {"name": "DefaultAutomationPolicy", "layer": "Risk", "status": "CONNECTED", "description": "Default risk-based automation routing"},
    {"name": "LogisticsAutomationPolicy", "layer": "Risk", "status": "CONNECTED", "description": "Logistics-specific risk automation"},
    {"name": "TriageEngine", "layer": "Application", "status": "CONNECTED", "description": "Application-layer orchestrator"},
    {"name": "PromptBuilder", "layer": "Application", "status": "CONNECTED", "description": "Structured prompt construction"},
    {"name": "ReliabilityPipeline", "layer": "Reliability", "status": "CONNECTED", "description": "Parse \u2192 Schema \u2192 Semantic \u2192 Domain validation + retry"},
    {"name": "AutomationEvaluator", "layer": "Risk", "status": "CONNECTED", "description": "Risk assessment and automation routing"},
    {"name": "MockProvider", "layer": "Providers", "status": "CONNECTED", "description": "Deterministic test/demo provider"},
    {"name": "OllamaProvider", "layer": "Providers", "status": "TESTED_ISOLATED", "description": "Local LLM provider (requires Ollama)"},
    {"name": "CloudProvider", "layer": "Providers", "status": "TESTED_ISOLATED", "description": "OpenAI-compatible cloud provider"},
    {"name": "SQLite DecisionRepository", "layer": "Persistence", "status": "CONNECTED", "description": "Decision persistence with lifecycle tracking"},
    {"name": "SQLite AuditAdapter", "layer": "Persistence", "status": "CONNECTED", "description": "Audit event persistence"},
    {"name": "FastAPI", "layer": "API", "status": "CONNECTED", "description": "HTTP transport layer"},
    {"name": "Streamlit", "layer": "UI", "status": "CONNECTED", "description": "Decision control console"},
    {"name": "HITL", "layer": "Human Oversight", "status": "CONNECTED", "description": "Approve/Reject/Escalate/Modify lifecycle"},
]

ISOLATED_EXTENSIONS = [
    {"name": "Logistics Intelligence", "layer": "Domain", "status": "TESTED_ISOLATED", "description": "Shipment understanding, carrier matching, route recommendation", "modules": 7, "tests": 0},
    {"name": "RealEstatePolicy", "layer": "Domain", "status": "TESTED_ISOLATED", "description": "Real estate domain policy (not registered)", "modules": 1, "tests": 28},
    {"name": "Specialist Models", "layer": "ML", "status": "TESTED_ISOLATED", "description": "Keyword-based classification/risk", "modules": 2, "tests": 21},
    {"name": "Hybrid Decision Engine", "layer": "Decision", "status": "TESTED_ISOLATED", "description": "Multi-source decision combination", "modules": 1, "tests": 18},
    {"name": "ML Adaptation", "layer": "ML", "status": "TESTED_ISOLATED", "description": "Training abstractions, dataset pipeline", "modules": 7, "tests": 26},
    {"name": "Governance", "layer": "Governance", "status": "TESTED_ISOLATED", "description": "Security, compliance, RBAC", "modules": 1, "tests": 28},
    {"name": "Production", "layer": "Infrastructure", "status": "TESTED_ISOLATED", "description": "Circuit breaker, rate limiter, health checks", "modules": 1, "tests": 28},
    {"name": "Evaluation Runner", "layer": "Evaluation", "status": "TESTED_ISOLATED", "description": "Dataset evaluation framework", "modules": 4, "tests": 15},
    {"name": "Bias Evaluator", "layer": "Evaluation", "status": "TESTED_ISOLATED", "description": "Counterfactual invariance evaluation", "modules": 2, "tests": 14},
    {"name": "Cost Model", "layer": "Evaluation", "status": "TESTED_ISOLATED", "description": "Token-based cost estimation", "modules": 1, "tests": 8},
]

STATUS_COLORS = {
    "CONNECTED": "#1a7a4a",
    "TESTED_ISOLATED": "#a06800",
    "PARTIALLY_CONNECTED": "#c06020",
    "NOT_AVAILABLE": "#b82e2e",
}

_FLOW_STEPS = [
    ("STREAMLIT", "UI"),
    ("FASTAPI", "API"),
    ("TRIAGE ENGINE", "Application"),
    ("PROVIDER ABSTRACTION", "Ports"),
    ("PYDANTIC CONTRACTS", "Foundation"),
    ("RELIABILITY PIPELINE", "Reliability"),
    ("DOMAIN / RISK", "Domain + Risk"),
    ("DECISION", "Decision"),
    ("HITL", "Human Oversight"),
    ("SQLITE / AUDIT", "Persistence"),
]

_LAYER_RULES = [
    "Dependencies flow DOWNWARD only (UI \u2192 API \u2192 Application \u2192 Domain \u2192 Ports)",
    "Infrastructure implements Ports, never the reverse",
    "Domain never imports Infrastructure",
    "Providers never make final business decisions",
    "Reliability validates all external output",
    "Risk increases human involvement, never decreases it",
    "Everything important is auditable",
]

_LAYER_MAP = [
    ("UI", "Streamlit / Presentation", "CONNECTED"),
    ("API", "FastAPI / HTTP Transport", "CONNECTED"),
    ("Application", "TriageEngine / Orchestration", "CONNECTED"),
    ("Domain", "Policies / Domain Rules", "CONNECTED"),
    ("Ports", "Interfaces / Abstractions", "CONNECTED"),
    ("Providers", "LLM / External Services", "CONNECTED"),
    ("Reliability", "Validation / Retry / Repair", "CONNECTED"),
    ("Risk", "Automation / Routing Safety", "CONNECTED"),
    ("Persistence", "SQLite / Decision + Audit", "CONNECTED"),
    ("Human Oversight", "HITL / Override / Escalation", "CONNECTED"),
    ("Audit", "Traceability / Event Log", "CONNECTED"),
    ("Evaluation", "Measurement / Bias / Cost", "TESTED_ISOLATED"),
    ("ML", "Specialist / Adaptation", "TESTED_ISOLATED"),
    ("Governance", "Security / Compliance", "TESTED_ISOLATED"),
    ("Production", "Circuit Breaker / Rate Limiter", "TESTED_ISOLATED"),
]


def render() -> None:
    st.markdown(
        f'<div class="case-page-title">{t("arch_title")}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="case-page-subtitle">{t("arch_subtitle")}</div>',
        unsafe_allow_html=True,
    )

    tab_connected, tab_isolated, tab_layers = st.tabs(
        [t("arch_connected"), t("arch_isolated"), t("arch_layers")]
    )

    with tab_connected:
        _render_connected()
    with tab_isolated:
        _render_isolated()
    with tab_layers:
        _render_layers()


def _status_badge(status: str) -> str:
    color = STATUS_COLORS.get(status, "#555a68")
    return (
        f'<span class="case-badge" '
        f'style="background:{color}12; color:{color};">{status}</span>'
    )


def _render_connected() -> None:
    st.markdown(f"#### {t('arch_connected')}")
    st.caption(t("arch_connected_desc"))

    _render_flow_diagram()

    st.markdown("---")
    st.markdown("##### Componentes por Capa")

    layers: dict[str, list[dict[str, str]]] = {}
    for c in CONNECTED_COMPONENTS:
        layers.setdefault(c["layer"], []).append(c)

    for layer, components in layers.items():
        with st.expander(f"{layer} ({len(components)})", expanded=False):
            for c in components:
                color = STATUS_COLORS.get(c["status"], "#555a68")
                st.markdown(
                    f'<div style="display:flex; align-items:center; gap:8px; padding:4px 0;">'
                    f'<span style="display:inline-block; width:8px; height:8px; '
                    f'border-radius:50%; background:{color};"></span>'
                    f'<strong>{c["name"]}</strong>'
                    f'{_status_badge(c["status"])}'
                    f'</div>'
                    f'<div style="font-size:0.78rem; color:var(--text-secondary); '
                    f'margin-left:16px;">{c["description"]}</div>',
                    unsafe_allow_html=True,
                )


def _render_flow_diagram() -> None:
    st.markdown("##### Flujo de Decisiones")
    st.caption("Flujo visual desde la entrada del usuario hasta la persistencia")

    connector = (
        '<div style="text-align:center; color:var(--text-secondary); '
        'font-size:1.1rem; padding:2px 0;">\u2193</div>'
    )

    for step_name, layer in _FLOW_STEPS:
        st.markdown(
            f'<div style="background:var(--background-secondary, #f0f2f6); '
            f'border:1px solid var(--border-color, #e0e2e8); '
            f'border-radius:6px; padding:8px 16px; text-align:center; '
            f'margin:0 40px;">'
            f'<span style="font-weight:700; letter-spacing:0.5px;">{step_name}</span>'
            f' <span style="font-size:0.75rem; color:var(--text-secondary);">'
            f'{layer}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown(connector, unsafe_allow_html=True)

    providers = [c for c in CONNECTED_COMPONENTS if c["layer"] == "Providers"]
    provider_lines = "".join(
        f'<div style="padding:2px 0;">{p["name"]} '
        f'{_status_badge(p["status"])}</div>'
        for p in providers
    )
    st.markdown(
        f'<div style="text-align:center; margin:0 40px; padding:10px 16px; '
        f'border:1px dashed var(--border-color, #e0e2e8); border-radius:6px;">'
        f'<div style="font-weight:600; margin-bottom:4px; font-size:0.85rem;">'
        f'Proveedores LLM</div>'
        f'{provider_lines}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(connector, unsafe_allow_html=True)


def _render_isolated() -> None:
    st.markdown(f"#### {t('arch_isolated')}")
    st.caption(t("arch_isolated_desc"))

    modules_total: int = sum(e["modules"] for e in ISOLATED_EXTENSIONS)  # type: ignore[misc]
    tests_total: int = sum(e["tests"] for e in ISOLATED_EXTENSIONS)  # type: ignore[misc]
    render_metric_cards([
        {"label": "Extensiones", "value": str(len(ISOLATED_EXTENSIONS)), "icon": "\u2699\ufe0f", "color": "#a06800"},
        {"label": "M\u00f3dulos", "value": str(modules_total), "icon": "\U0001f4e6", "color": "#a06800"},
        {"label": "Tests", "value": str(tests_total), "icon": "\U0001f9ea", "color": "#1a7a4a"},
    ])

    st.markdown("")

    for ext in ISOLATED_EXTENSIONS:
        with st.container(border=True):
            c1, c2, c3 = st.columns([4, 2, 1])
            with c1:
                st.markdown(f"**{ext['name']}**")
                st.caption(ext["description"])
            with c2:
                st.caption(f"Capa: {ext['layer']}")
                st.caption(f"{ext['modules']} m\u00f3dulos \u00b7 {ext['tests']} tests")
            with c3:
                st.markdown(_status_badge(str(ext["status"])), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander(t("arch_integration")):
        st.markdown(
            "Los m\u00f3dulos aislados NO est\u00e1n conectados al pipeline en ejecuci\u00f3n "
            "a menos que se cumplan las siguientes condiciones:\n\n"
            "1. Problema real identificado\n"
            "2. Datos suficientes disponibles\n"
            "3. Baseline establecido\n"
            "4. Costo de integraci\u00f3n justificado\n"
            "5. Decisi\u00f3n arquitect\u00f3nica documentada\n"
            "6. Tests pasan\n"
            "7. Verificaci\u00f3n manual completa\n\n"
            "Ver `docs/FUTURE_EVOLUTION.md` para el marco de decisi\u00f3n completo."
        )


def _render_layers() -> None:
    st.markdown(f"#### {t('arch_layer_map')}")
    st.caption(t("arch_layer_desc"))

    for name, desc, status in _LAYER_MAP:
        color = STATUS_COLORS.get(status, "#555a68")
        st.markdown(
            f'<div style="display:flex; align-items:center; gap:12px; padding:6px 0; '
            f'border-left:3px solid {color}; padding-left:12px; margin-bottom:4px;">'
            f'<strong style="min-width:140px;">{name}</strong>'
            f'<span style="font-size:0.85rem; color:var(--text-secondary);">{desc}</span>'
            f'<span style="margin-left:auto;">{_status_badge(status)}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander(t("arch_dep_rules")):
        rules_md = "\n".join(f"- {r}" for r in _LAYER_RULES)
        st.markdown(rules_md)
