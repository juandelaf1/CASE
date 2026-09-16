from __future__ import annotations

import streamlit as st

from streamlit_app.i18n import t

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


def render() -> None:
    st.markdown(f'<div class="case-page-title">{t("arch_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="case-page-subtitle">{t("arch_subtitle")}</div>', unsafe_allow_html=True)

    tab_connected, tab_isolated, tab_layers = st.tabs([t("arch_connected"), t("arch_isolated"), t("arch_layers")])

    with tab_connected:
        _render_connected()

    with tab_isolated:
        _render_isolated()

    with tab_layers:
        _render_layers()


def _render_connected() -> None:
    st.markdown(f"#### {t('arch_connected')}")
    st.caption(t("arch_connected_desc"))

    layers: dict[str, list[dict]] = {}
    for c in CONNECTED_COMPONENTS:
        layer = c["layer"]
        if layer not in layers:
            layers[layer] = []
        layers[layer].append(c)

    for layer, components in layers.items():
        with st.expander(f"{layer} ({len(components)})", expanded=True):
            for c in components:
                color = STATUS_COLORS.get(c["status"], "#555a68")
                st.markdown(
                    f'<div style="display:flex; align-items:center; gap:8px; padding:4px 0;">'
                    f'<span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:{color};"></span>'
                    f'<strong>{c["name"]}</strong>'
                    f'<span class="case-badge" style="background:{color}12; color:{color};">{c["status"]}</span>'
                    f'</div>'
                    f'<div style="font-size:0.78rem; color:var(--text-secondary); margin-left:16px;">{c["description"]}</div>',
                    unsafe_allow_html=True,
                )


def _render_isolated() -> None:
    st.markdown(f"#### {t('arch_isolated')}")
    st.caption(t("arch_isolated_desc"))

    for ext in ISOLATED_EXTENSIONS:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"**{ext['name']}**")
                st.caption(f"{ext['description']} \u2014 Layer: {ext['layer']}")
            with c2:
                color = STATUS_COLORS.get(ext["status"], "#555a68")
                st.markdown(
                    f'<span class="case-badge" style="background:{color}12; color:{color};">{ext["status"]}</span>',
                    unsafe_allow_html=True,
                )
                st.caption(f"{ext['modules']} modules, {ext['tests']} tests")

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander(t("arch_integration")):
        st.markdown("""
Isolated modules are NOT connected to the running pipeline unless:

1. Real problem identified
2. Sufficient data available
3. Baseline established
4. Integration cost justified
5. Architectural decision documented
6. Tests pass
7. Manual verification complete

See `docs/FUTURE_EVOLUTION.md` for the full decision framework.
""")


def _render_layers() -> None:
    st.markdown(f"#### {t('arch_layer_map')}")
    st.caption(t("arch_layer_desc"))

    layers = [
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

    for _i, (name, desc, status) in enumerate(layers):
        color = STATUS_COLORS.get(status, "#555a68")
        st.markdown(
            f'<div style="display:flex; align-items:center; gap:12px; padding:6px 0; '
            f'border-left:3px solid {color}; padding-left:12px; margin-bottom:4px;">'
            f'<strong style="min-width:140px;">{name}</strong>'
            f'<span style="font-size:0.85rem; color:var(--text-secondary);">{desc}</span>'
            f'<span class="case-badge" style="background:{color}12; color:{color}; margin-left:auto;">{status}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with st.expander(t("arch_dep_rules")):
        st.markdown("""
- Dependencies flow DOWNWARD only (UI \u2192 API \u2192 Application \u2192 Domain \u2192 Ports)
- Infrastructure implements Ports, never the reverse
- Domain never imports Infrastructure
- Providers never make final business decisions
- Reliability validates all external output
- Risk increases human involvement, never decreases it
- Everything important is auditable
""")
