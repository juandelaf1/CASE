from __future__ import annotations

from html import escape as _html_escape

GLOBAL_CSS = """
<style>
/* ── CASE Light Theme — Desktop-optimized, professional scale ──── */
:root {
    /* Surfaces */
    --bg-page: #f4f5f7;
    --bg-surface: #ffffff;
    --bg-surface-alt: #f0f1f4;
    --bg-sidebar: #1c1f26;

    /* Borders */
    --border: #e0e2e8;
    --border-strong: #c5c9d2;

    /* Text */
    --text-primary: #1e2028;
    --text-secondary: #555a68;
    --text-muted: #8b90a0;
    --text-inverse: #e8eaef;

    /* Brand — silver from banner */
    --brand-silver: #a8b0bc;
    --brand-silver-light: #d0d4dc;

    /* Brand — teal / petroleum (primary interaction) */
    --brand-teal: #1a7a7a;
    --brand-teal-hover: #156666;
    --brand-teal-light: rgba(26,122,122,0.08);

    /* Semantic colors */
    --color-green: #1a7a4a;
    --color-green-bg: rgba(26,122,74,0.08);
    --color-green-border: rgba(26,122,74,0.20);
    --color-amber: #a06800;
    --color-amber-bg: rgba(160,104,0,0.08);
    --color-amber-border: rgba(160,104,0,0.20);
    --color-red: #b82e2e;
    --color-red-bg: rgba(184,46,46,0.08);
    --color-red-border: rgba(184,46,46,0.20);
    --color-blue: #1a5a9a;
    --color-blue-bg: rgba(26,90,154,0.08);
    --color-blue-border: rgba(26,90,154,0.18);
    --color-purple: #6a4fa0;
    --color-purple-bg: rgba(106,79,160,0.08);

    /* Risk */
    --risk-low: var(--color-green);
    --risk-medium: var(--color-amber);
    --risk-high: #c06020;
    --risk-critical: var(--color-red);

    /* Section semantic */
    --proposal-bg: var(--color-blue-bg);
    --proposal-border: var(--color-blue);
    --decision-bg: var(--color-green-bg);
    --decision-border: var(--color-green);
    --validation-bg: var(--bg-surface-alt);
    --validation-border: var(--border-strong);
    --governance-bg: var(--color-purple-bg);
    --governance-border: var(--color-purple);
}

/* ── Streamlit overrides — wider, more breathing room ──────────── */
[data-testid="stAppViewContainer"] { background: var(--bg-page); }
[data-testid="stHeader"] { background: var(--bg-page); }
.block-container { padding-top: 1.5rem !important; padding-bottom: 1rem !important; }
[data-testid="stMain"] { max-width: 1400px; margin: 0 auto; }

/* ── Typography Scale ─────────────────────────────────────────── */
h1, h2, h3, h4, h5, h6, [data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2, [data-testid="stMarkdownContainer"] h3 {
    color: var(--text-primary) !important;
}
[data-testid="stMarkdownContainer"] p {
    font-size: 1.05rem;
    line-height: 1.65;
    color: var(--text-secondary);
}

/* ── Sidebar ──────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: var(--bg-sidebar);
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown span,
[data-testid="stSidebar"] label {
    color: var(--text-inverse) !important;
}
.sidebar-brand {
    padding: 0.5rem 0 0.8rem;
    margin-bottom: 0.5rem;
}
.sidebar-brand-name {
    font-size: 1.6rem;
    font-weight: 800;
    color: #e8eaef;
    letter-spacing: -0.02em;
}
.sidebar-brand-sub {
    font-size: 0.82rem;
    color: var(--brand-silver);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 3px;
}
.sidebar-nav-section {
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--brand-silver);
    margin-bottom: 0.4rem;
    margin-top: 0.8rem;
}
.sidebar-logo-img {
    width: 100%;
    max-height: 90px;
    object-fit: contain;
    margin-bottom: 0.6rem;
    border-radius: 6px;
}

/* ── Hero ─────────────────────────────────────────────────────── */
.case-hero {
    text-align: center;
    padding: 2.5rem 2rem 2rem;
    margin-bottom: 1.5rem;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 12px;
}
.case-hero-title {
    font-size: 2.8rem;
    font-weight: 800;
    color: var(--text-primary);
    letter-spacing: -0.03em;
    margin-bottom: 0.3rem;
}
.case-hero-subtitle {
    font-size: 1.2rem;
    color: var(--brand-teal);
    font-weight: 600;
    margin-bottom: 0.8rem;
}
.case-hero-desc {
    font-size: 1.05rem;
    color: var(--text-secondary);
    max-width: 680px;
    margin: 0 auto;
    line-height: 1.65;
}
.case-hero-tagline {
    font-size: 0.92rem;
    color: var(--text-muted);
    margin-top: 0.8rem;
    font-style: italic;
}

/* ── Pipeline Visual ──────────────────────────────────────────── */
.case-pipeline {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    padding: 1rem 0.5rem;
    margin: 1rem 0;
    overflow-x: auto;
    flex-wrap: nowrap;
}
.case-pipeline-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.35rem;
    min-width: 85px;
    flex-shrink: 0;
}
.case-pipeline-icon {
    width: 38px;
    height: 38px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
    font-weight: 700;
    color: var(--brand-teal);
    background: var(--brand-teal-light);
}
.case-pipeline-label {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-muted);
    text-align: center;
    white-space: nowrap;
}
.case-pipeline-arrow {
    color: var(--border-strong);
    font-size: 1rem;
    margin: 0 0.15rem;
    flex-shrink: 0;
    align-self: flex-start;
    padding-top: 0.6rem;
}

/* ── Metric Cards ─────────────────────────────────────────────── */
.case-metric-card {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.2rem 1.1rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}
.case-metric-icon {
    font-size: 1.6rem;
    width: 48px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 10px;
    flex-shrink: 0;
}
.case-metric-body {
    display: flex;
    flex-direction: column;
    min-width: 0;
}
.case-metric-value {
    font-size: 1.8rem;
    font-weight: 700;
    line-height: 1.1;
    color: var(--text-primary);
}
.case-metric-label {
    font-size: 0.82rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-top: 3px;
}

/* ── Section Containers ───────────────────────────────────────── */
.case-section {
    border-radius: 8px;
    padding: 1.2rem 1.3rem;
    margin-bottom: 1rem;
    border-left: 4px solid;
    background: var(--bg-surface);
}
.case-section-proposal { border-left-color: var(--proposal-border); background: var(--proposal-bg); }
.case-section-validation { border-left-color: var(--validation-border); background: var(--validation-bg); }
.case-section-decision { border-left-color: var(--decision-border); background: var(--decision-bg); }
.case-section-governance { border-left-color: var(--governance-border); background: var(--governance-bg); }
.case-section-title {
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-secondary);
    margin-bottom: 0.6rem;
}

/* ── Decision Hero ────────────────────────────────────────────── */
.case-decision-hero {
    text-align: center;
    padding: 2rem 1.5rem;
    border-radius: 12px;
    margin-bottom: 1.2rem;
}
.case-decision-hero-action {
    font-size: 2.4rem;
    font-weight: 800;
    letter-spacing: 0.02em;
    margin-bottom: 0.3rem;
}
.case-decision-hero-lifecycle {
    font-size: 0.92rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.case-decision-hero-approve { background: var(--color-green-bg); border: 1px solid var(--color-green-border); }
.case-decision-hero-approve .case-decision-hero-action { color: var(--color-green); }
.case-decision-hero-approve .case-decision-hero-lifecycle { color: var(--color-green); }
.case-decision-hero-reject { background: var(--color-red-bg); border: 1px solid var(--color-red-border); }
.case-decision-hero-reject .case-decision-hero-action { color: var(--color-red); }
.case-decision-hero-reject .case-decision-hero-lifecycle { color: var(--color-red); }
.case-decision-hero-escalate { background: rgba(192,96,32,0.08); border: 1px solid rgba(192,96,32,0.20); }
.case-decision-hero-escalate .case-decision-hero-action { color: var(--risk-high); }
.case-decision-hero-escalate .case-decision-hero-lifecycle { color: var(--risk-high); }
.case-decision-hero-review { background: var(--color-amber-bg); border: 1px solid var(--color-amber-border); }
.case-decision-hero-review .case-decision-hero-action { color: var(--color-amber); }
.case-decision-hero-review .case-decision-hero-lifecycle { color: var(--color-amber); }

/* ── Case Card ────────────────────────────────────────────────── */
.case-selector-card {
    background: var(--bg-surface);
    border: 2px solid var(--border);
    border-radius: 10px;
    padding: 1.2rem;
    cursor: pointer;
    transition: border-color 0.15s;
}
.case-selector-card:hover { border-color: var(--brand-teal); }
.case-selector-card.selected { border-color: var(--brand-teal); background: var(--brand-teal-light); }
.case-selector-label {
    font-size: 1.0rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 0.2rem;
}
.case-selector-id {
    font-size: 0.82rem;
    color: var(--text-muted);
    margin-bottom: 0.4rem;
}
.case-selector-meta {
    font-size: 0.9rem;
    color: var(--text-secondary);
    line-height: 1.5;
}

/* ── Badges ───────────────────────────────────────────────────── */
.case-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.18rem 0.65rem;
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    white-space: nowrap;
}
.case-badge-low { background: var(--color-green-bg); color: var(--color-green); }
.case-badge-medium { background: var(--color-amber-bg); color: var(--color-amber); }
.case-badge-high { background: rgba(192,96,32,0.10); color: var(--risk-high); }
.case-badge-critical { background: var(--color-red-bg); color: var(--color-red); }
.case-badge-auto { background: var(--color-green-bg); color: var(--color-green); }
.case-badge-review { background: var(--color-amber-bg); color: var(--color-amber); }
.case-badge-escalate { background: var(--color-red-bg); color: var(--color-red); }
.case-badge-modified { background: var(--color-purple-bg); color: var(--color-purple); }
.case-badge-approved { background: var(--color-green-bg); color: var(--color-green); }
.case-badge-rejected { background: var(--color-red-bg); color: var(--color-red); }
.case-badge-proposed { background: var(--color-blue-bg); color: var(--color-blue); }
.case-badge-ai-proposed { background: var(--color-blue-bg); color: var(--color-blue); }
.case-badge-under-review { background: var(--color-amber-bg); color: var(--color-amber); }
.case-badge-escalated { background: var(--color-red-bg); color: var(--color-red); }

/* ── Confidence Bar ───────────────────────────────────────────── */
.case-confidence-bar {
    width: 100%;
    height: 8px;
    background: var(--bg-surface-alt);
    border-radius: 4px;
    overflow: hidden;
    margin-top: 4px;
}
.case-confidence-fill {
    height: 100%;
    border-radius: 4px;
}

/* ── Field Rows ───────────────────────────────────────────────── */
.case-field-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--border);
    gap: 1rem;
}
.case-field-row:last-child { border-bottom: none; }
.case-field-label {
    font-size: 0.92rem;
    color: var(--text-muted);
    flex-shrink: 0;
    min-width: 120px;
}
.case-field-value {
    font-size: 0.95rem;
    color: var(--text-primary);
    text-align: right;
    word-break: break-word;
    font-weight: 500;
}

/* ── Timeline ─────────────────────────────────────────────────── */
.case-timeline-event {
    display: flex;
    gap: 0.9rem;
    padding: 0.65rem 0;
    border-bottom: 1px solid var(--border);
}
.case-timeline-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    margin-top: 6px;
    flex-shrink: 0;
}
.case-timeline-body { flex: 1; min-width: 0; }
.case-timeline-type { font-size: 0.92rem; font-weight: 600; color: var(--text-primary); }
.case-timeline-meta { font-size: 0.82rem; color: var(--text-muted); margin-top: 2px; }
.case-timeline-details { font-size: 0.88rem; color: var(--text-secondary); margin-top: 3px; }

/* ── Comparison ───────────────────────────────────────────────── */
.case-comparison-col {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.2rem;
}
.case-comparison-header {
    font-size: 0.95rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-primary);
    text-align: center;
    padding-bottom: 0.6rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 0.7rem;
}
.case-comparison-row {
    display: flex;
    justify-content: space-between;
    padding: 0.4rem 0;
    border-bottom: 1px solid var(--border);
}
.case-comparison-row:last-child { border-bottom: none; }
.case-comparison-label { font-size: 0.85rem; color: var(--text-muted); }
.case-comparison-value { font-size: 0.92rem; color: var(--text-primary); font-weight: 600; }

/* ── Utility ──────────────────────────────────────────────────── */
.case-arrow-down {
    text-align: center;
    color: var(--border-strong);
    font-size: 1.4rem;
    padding: 0.3rem 0;
}
.case-empty-state {
    text-align: center;
    padding: 3.5rem 1.5rem;
    color: var(--text-muted);
    font-size: 1.05rem;
}
.case-page-title {
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 0.2rem;
}
.case-page-subtitle {
    font-size: 0.95rem;
    color: var(--text-secondary);
    margin-bottom: 1.2rem;
}
.case-section-educational {
    background: var(--brand-teal-light);
    border: 1px solid rgba(26,122,122,0.15);
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    margin-top: 0.5rem;
}
.case-section-educational p {
    font-size: 0.92rem;
    color: var(--text-secondary);
    margin: 0;
    line-height: 1.6;
}
.case-provider-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.3rem 0.75rem;
    border-radius: 8px;
    font-size: 0.88rem;
    font-weight: 600;
    background: var(--brand-teal-light);
    color: var(--brand-teal);
    border: 1px solid rgba(26,122,122,0.18);
}
.case-flow-connector {
    text-align: center;
    color: var(--border-strong);
    font-size: 1rem;
    padding: 0.2rem 0;
}

/* ── Backend Offline ──────────────────────────────────────────── */
.case-offline-box {
    text-align: center;
    padding: 4rem 3rem;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    max-width: 560px;
    margin: 3rem auto;
}
.case-offline-title {
    font-size: 1.3rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 0.6rem;
}
.case-offline-desc {
    font-size: 1rem;
    color: var(--text-secondary);
    margin-bottom: 0.4rem;
}
.case-offline-code {
    font-size: 0.88rem;
    color: var(--text-muted);
    font-family: monospace;
    background: var(--bg-surface-alt);
    padding: 0.4rem 0.8rem;
    border-radius: 6px;
    display: inline-block;
    margin-top: 0.6rem;
}

/* ── Tables ───────────────────────────────────────────────────── */
.case-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.92rem;
}
.case-table th {
    text-align: left;
    font-weight: 700;
    color: var(--text-secondary);
    padding: 0.6rem 0.8rem;
    border-bottom: 2px solid var(--border-strong);
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.case-table td {
    padding: 0.6rem 0.8rem;
    border-bottom: 1px solid var(--border);
    color: var(--text-primary);
}
.case-table tr:last-child td { border-bottom: none; }

/* ── Buttons override ─────────────────────────────────────────── */
.stButton > button {
    font-size: 0.95rem !important;
    padding: 0.5rem 1.5rem !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
}
.stDownloadButton > button {
    font-size: 0.92rem !important;
}
</style>
"""


def inject_global_css() -> None:
    import streamlit as st
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def metric_card(label: str, value: str, icon: str, color: str = "#1a7a7a") -> str:
    safe_label = _html_escape(label)
    safe_value = _html_escape(value)
    safe_color = _html_escape(color)
    return (
        f'<div class="case-metric-card">'
        f'<div class="case-metric-icon" style="background:{safe_color}12; color:{safe_color};">{icon}</div>'
        f'<div class="case-metric-body">'
        f'<div class="case-metric-value">{safe_value}</div>'
        f'<div class="case-metric-label">{safe_label}</div>'
        f'</div></div>'
    )


def confidence_bar_html(score: float) -> str:
    if score >= 0.7:
        color = "#1a7a4a"
    elif score >= 0.4:
        color = "#a06800"
    else:
        color = "#b82e2e"
    pct = max(0.0, min(1.0, score)) * 100
    return (
        f'<div class="case-confidence-bar">'
        f'<div class="case-confidence-fill" style="width:{pct:.0f}%; background:{color};"></div>'
        f'</div>'
    )


def risk_badge_class(level: str) -> str:
    if not level or not isinstance(level, str):
        return "case-badge-low"
    mapping = {
        "LOW": "case-badge-low",
        "MEDIUM": "case-badge-medium",
        "HIGH": "case-badge-high",
        "CRITICAL": "case-badge-critical",
    }
    return mapping.get(level.upper(), "case-badge-low")


def lifecycle_badge_class(lifecycle: str) -> str:
    if not lifecycle or not isinstance(lifecycle, str):
        return "case-badge-proposed"
    mapping = {
        "ai_proposed": "case-badge-ai-proposed",
        "under_review": "case-badge-under-review",
        "approved": "case-badge-approved",
        "rejected": "case-badge-rejected",
        "modified": "case-badge-modified",
        "escalated": "case-badge-escalated",
    }
    return mapping.get(lifecycle, "case-badge-proposed")


def action_color(action: str) -> str:
    mapping = {
        "auto_approve": "#1a7a4a",
        "approve": "#1a7a4a",
        "human_review": "#a06800",
        "reject": "#b82e2e",
        "escalate": "#c06020",
        "modify": "#6a4fa0",
    }
    return mapping.get(action, "#1a7a7a")


def event_type_color(event_type: str) -> str:
    if not event_type:
        return "#1a7a7a"
    low = event_type.lower()
    if "approve" in low:
        return "#1a7a4a"
    if "reject" in low:
        return "#b82e2e"
    if "modify" in low:
        return "#6a4fa0"
    if "escalat" in low:
        return "#c06020"
    if "review" in low:
        return "#a06800"
    return "#1a7a7a"
