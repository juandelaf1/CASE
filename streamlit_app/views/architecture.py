from __future__ import annotations

import streamlit as st

from streamlit_app.i18n import t
from streamlit_app.ui.components import render_metric_cards

CONNECTED_COMPONENTS = [
    {"name": "Contracts", "layer": "Foundation", "status": "CONNECTED", "description": "Modelos Pydantic v2 en todos los limites publicos"},
    {"name": "LLMProvider", "layer": "Ports", "status": "CONNECTED", "description": "Abstraccion de LLM agnostica al proveedor"},
    {"name": "DomainRegistry", "layer": "Domain", "status": "CONNECTED", "description": "Registro y resolucion de politicas de dominio"},
    {"name": "UrbanPolicy", "layer": "Domain", "status": "CONNECTED", "description": "Politica de dominio de operaciones urbanas"},
    {"name": "LogisticsPolicy", "layer": "Domain", "status": "CONNECTED", "description": "Politica de dominio logistico"},
    {"name": "InfrastructurePolicy", "layer": "Domain", "status": "CONNECTED", "description": "Politica de dominio de infraestructura"},
    {"name": "SeismicRiskPolicy", "layer": "Domain", "status": "CONNECTED", "description": "Politica de dominio de riesgo sismico"},
    {"name": "DefaultAutomationPolicy", "layer": "Risk", "status": "CONNECTED", "description": "Enrutamiento de automatizacion basado en riesgo por defecto"},
    {"name": "LogisticsAutomationPolicy", "layer": "Risk", "status": "CONNECTED", "description": "Automatizacion de riesgo especifica para logistica"},
    {"name": "SeismicAutomationPolicy", "layer": "Risk", "status": "CONNECTED", "description": "Automatizacion de riesgo especifica para sismos"},
    {"name": "TriageEngine", "layer": "Application", "status": "CONNECTED", "description": "Orquestador de la capa de aplicacion"},
    {"name": "PromptBuilder", "layer": "Application", "status": "CONNECTED", "description": "Construccion estructurada de prompts"},
    {"name": "ReliabilityPipeline", "layer": "Reliability", "status": "CONNECTED", "description": "Parse \u2192 Schema \u2192 Semantico \u2192 Dominio + reintentos"},
    {"name": "AutomationEvaluator", "layer": "Risk", "status": "CONNECTED", "description": "Evaluacion de riesgo y enrutamiento de automatizacion"},
    {"name": "CostModel", "layer": "Evaluation", "status": "CONNECTED", "description": "Estimacion de costos basada en tokens"},
    {"name": "MockProvider", "layer": "Providers", "status": "CONNECTED", "description": "Proveedor de prueba/demo determinista"},
    {"name": "SQLite DecisionRepository", "layer": "Persistence", "status": "CONNECTED", "description": "Persistencia de decisiones con seguimiento de ciclo de vida"},
    {"name": "SQLite AuditAdapter", "layer": "Persistence", "status": "CONNECTED", "description": "Persistencia de eventos de auditoria"},
    {"name": "FastAPI", "layer": "API", "status": "CONNECTED", "description": "Capa de transporte HTTP"},
    {"name": "Streamlit", "layer": "UI", "status": "CONNECTED", "description": "Consola de control de decisiones"},
    {"name": "HITL", "layer": "Human Oversight", "status": "CONNECTED", "description": "Ciclo Aprobar/Rechazar/Escalar/Modificar"},
]

ISOLATED_EXTENSIONS = [
    {"name": "OllamaProvider", "layer": "Providers", "status": "TESTED_ISOLATED", "description": "Proveedor LLM local (requiere Ollama)", "modules": 1, "tests": 10},
    {"name": "CloudProvider", "layer": "Providers", "status": "TESTED_ISOLATED", "description": "Proveedor cloud compatible con OpenAI", "modules": 1, "tests": 12},
    {"name": "Logistics Intelligence", "layer": "Domain", "status": "TESTED_ISOLATED", "description": "Comprension de envios, matching de transportistas, rutas", "modules": 7, "tests": 0},
    {"name": "RealEstatePolicy", "layer": "Domain", "status": "TESTED_ISOLATED", "description": "Politica de dominio inmobiliario (no registrada)", "modules": 1, "tests": 28},
    {"name": "Specialist Models", "layer": "ML", "status": "TESTED_ISOLATED", "description": "Clasificacion y riesgo basados en keywords", "modules": 2, "tests": 21},
    {"name": "Hybrid Decision Engine", "layer": "Decision", "status": "TESTED_ISOLATED", "description": "Combinacion de decisiones multi-fuente", "modules": 1, "tests": 18},
    {"name": "ML Adaptation", "layer": "ML", "status": "TESTED_ISOLATED", "description": "Abstracciones de entrenamiento, pipeline de datasets", "modules": 7, "tests": 26},
    {"name": "Governance", "layer": "Governance", "status": "TESTED_ISOLATED", "description": "Seguridad, compliance, RBAC", "modules": 1, "tests": 28},
    {"name": "Production", "layer": "Infrastructure", "status": "TESTED_ISOLATED", "description": "Circuit breaker, rate limiter, health checks", "modules": 1, "tests": 28},
    {"name": "Evaluation Runner", "layer": "Evaluation", "status": "TESTED_ISOLATED", "description": "Framework de evaluacion con datasets", "modules": 4, "tests": 15},
    {"name": "Bias Evaluator", "layer": "Evaluation", "status": "TESTED_ISOLATED", "description": "Evaluacion de invariancia contrafactual", "modules": 2, "tests": 14},
]

STATUS_COLORS = {
    "CONNECTED": "#1a7a4a",
    "TESTED_ISOLATED": "#a06800",
    "PARTIALLY_CONNECTED": "#c06020",
    "NOT_AVAILABLE": "#b82e2e",
}

_FLOW_STEPS = [
    ("STREAMLIT", "Interfaz de usuario"),
    ("FASTAPI", "Transporte HTTP"),
    ("TRIAGE ENGINE", "Orquestacion"),
    ("PROMPT BUILDER", "Construccion de prompts"),
    ("PROVIDER ABSTRACTION", "Agnostico a proveedores"),
    ("RELIABILITY PIPELINE", "Validacion y reparacion"),
    ("DOMAIN + RISK", "Politicas y riesgo"),
    ("DECISION", "Decision final"),
    ("HITL", "Supervision humana"),
    ("SQLITE + AUDIT", "Persistencia y trazabilidad"),
]

_LAYER_RULES = [
    "Las dependencias fluyen SOLO HACIA ABAJO (UI \u2192 API \u2192 Application \u2192 Domain \u2192 Ports)",
    "La infraestructura implementa Ports, nunca al reves",
    "El dominio nunca importa infraestructura",
    "Los proveedores nunca toman decisiones de negocio finales",
    "La fiabilidad valida toda salida externa",
    "El riesgo aumenta la participacion humana, nunca la disminuye",
    "Todo lo importante es auditable",
]

_LAYER_MAP = [
    ("UI", "Streamlit / Presentacion", "CONNECTED"),
    ("API", "FastAPI / Transporte HTTP", "CONNECTED"),
    ("Application", "TriageEngine / Orquestacion", "CONNECTED"),
    ("Domain", "Politicas / Reglas de Dominio", "CONNECTED"),
    ("Ports", "Interfaces / Abstracciones", "CONNECTED"),
    ("Providers", "LLM / Servicios Externos", "CONNECTED"),
    ("Reliability", "Validacion / Reintentos / Reparacion", "CONNECTED"),
    ("Risk", "Automatizacion / Seguridad de Enrutamiento", "CONNECTED"),
    ("Persistence", "SQLite / Decision + Auditoria", "CONNECTED"),
    ("Human Oversight", "HITL / Anulacion / Escalamiento", "CONNECTED"),
    ("Audit", "Trazabilidad / Log de Eventos", "CONNECTED"),
    ("Evaluation", "Medicion / Sesion / Costo", "TESTED_ISOLATED"),
    ("ML", "Especialista / Adaptacion", "TESTED_ISOLATED"),
    ("Governance", "Seguridad / Compliance", "TESTED_ISOLATED"),
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

    connected_count = len([c for c in CONNECTED_COMPONENTS if c["status"] == "CONNECTED"])
    isolated_count = len(ISOLATED_EXTENSIONS)
    layers_count = len(_LAYER_MAP)
    rules_count = len(_LAYER_RULES)

    render_metric_cards([
        {"label": "Componentes Conectados", "value": str(connected_count), "icon": "\u2699\ufe0f", "color": "#1a7a4a"},
        {"label": "Extensiones Aisladas", "value": str(isolated_count), "icon": "\U0001f4e6", "color": "#a06800"},
        {"label": "Capas", "value": str(layers_count), "icon": "\U0001f3d7\ufe0f", "color": "#1a7a7a"},
        {"label": "Reglas", "value": str(rules_count), "icon": "\U0001f4cf", "color": "#b82e2e"},
    ])

    st.markdown("")

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
    label = status.replace("_", " ")
    return (
        f'<span class="case-badge" '
        f'style="background:{color}12; color:{color};">{label}</span>'
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

    modules_total = sum(e["modules"] for e in ISOLATED_EXTENSIONS)
    tests_total = sum(e["tests"] for e in ISOLATED_EXTENSIONS)
    render_metric_cards([
        {"label": "Extensiones", "value": str(len(ISOLATED_EXTENSIONS)), "icon": "\u2699\ufe0f", "color": "#a06800"},
        {"label": "Modulos", "value": str(modules_total), "icon": "\U0001f4e6", "color": "#a06800"},
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
                st.caption(f"{ext['modules']} modulos \u00b7 {ext['tests']} tests")
            with c3:
                st.markdown(_status_badge(str(ext["status"])), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander(t("arch_integration")):
        st.markdown(
            "Los modulos aislados NO estan conectados al pipeline en ejecucion "
            "a menos que se cumplan las siguientes condiciones:\n\n"
            "1. Problema real identificado\n"
            "2. Datos suficientes disponibles\n"
            "3. Baseline establecido\n"
            "4. Costo de integracion justificado\n"
            "5. Decision arquitectonica documentada\n"
            "6. Tests pasan\n"
            "7. Verificacion manual completa\n\n"
            "Ver `docs/FUTURE_EVOLUTION.md` para el marco de decision completo."
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
        st.markdown(
            "La arquitectura de CASE sigue reglas estrictas de dependencia para "
            "mantener la separacion de concernimientos y la mantenibilidad:\n"
        )
        rules_md = "\n".join(f"- {r}" for r in _LAYER_RULES)
        st.markdown(rules_md)
