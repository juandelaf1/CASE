from __future__ import annotations

GLOBAL_CSS = """
<style>
/* ── Base ────────────────────────────────────────────────── */
:root {
    --bg-primary: #0f1117;
    --bg-secondary: #161822;
    --bg-card: #1e2030;
    --bg-card-hover: #252840;
    --border-subtle: #2a2d3e;
    --border-accent: #3b3f54;
    --text-primary: #e2e4f0;
    --text-secondary: #8b8fa8;
    --text-muted: #5c5f77;

    --accent-blue: #4f8cf7;
    --accent-green: #34d399;
    --accent-yellow: #fbbf24;
    --accent-red: #f87171;
    --accent-purple: #a78bfa;
    --accent-cyan: #22d3ee;
    --accent-orange: #fb923c;

    --risk-low: #34d399;
    --risk-medium: #fbbf24;
    --risk-high: #fb923c;
    --risk-critical: #f87171;

    --proposal-bg: #1a1f35;
    --proposal-border: #4f8cf7;
    --decision-bg: #162019;
    --decision-border: #34d399;
    --validation-bg: #1c1c28;
    --validation-border: #5c5f77;
}

/* ── Metric Cards ────────────────────────────────────────── */
.case-metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    padding: 1.2rem 1rem;
    display: flex;
    align-items: center;
    gap: 0.9rem;
    transition: border-color 0.2s;
}
.case-metric-card:hover {
    border-color: var(--border-accent);
}
.case-metric-icon {
    font-size: 1.8rem;
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
    font-size: 1.7rem;
    font-weight: 700;
    line-height: 1.1;
    color: var(--text-primary);
}
.case-metric-label {
    font-size: 0.78rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-top: 2px;
}

/* ── Section Containers ──────────────────────────────────── */
.case-section {
    border-radius: 10px;
    padding: 1.1rem 1.2rem;
    margin-bottom: 1rem;
    border-left: 4px solid;
}
.case-section-proposal {
    background: var(--proposal-bg);
    border-left-color: var(--proposal-border);
}
.case-section-validation {
    background: var(--validation-bg);
    border-left-color: var(--validation-border);
}
.case-section-decision {
    background: var(--decision-bg);
    border-left-color: var(--decision-border);
}
.case-section-title {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.6rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}

/* ── Badges ──────────────────────────────────────────────── */
.case-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.15rem 0.55rem;
    border-radius: 9999px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    white-space: nowrap;
}
.case-badge-low { background: rgba(52,211,153,0.15); color: var(--risk-low); }
.case-badge-medium { background: rgba(251,191,36,0.15); color: var(--risk-medium); }
.case-badge-high { background: rgba(251,146,60,0.15); color: var(--risk-high); }
.case-badge-critical { background: rgba(248,113,113,0.15); color: var(--risk-critical); }
.case-badge-auto { background: rgba(52,211,153,0.15); color: var(--accent-green); }
.case-badge-review { background: rgba(251,191,36,0.15); color: var(--accent-yellow); }
.case-badge-escalate { background: rgba(248,113,113,0.15); color: var(--accent-red); }
.case-badge-modified { background: rgba(167,139,250,0.15); color: var(--accent-purple); }
.case-badge-approved { background: rgba(52,211,153,0.15); color: var(--accent-green); }
.case-badge-rejected { background: rgba(248,113,113,0.15); color: var(--accent-red); }
.case-badge-proposed { background: rgba(79,140,247,0.15); color: var(--accent-blue); }
.case-badge-ai-proposed { background: rgba(79,140,247,0.15); color: var(--accent-blue); }
.case-badge-under-review { background: rgba(251,191,36,0.15); color: var(--accent-yellow); }
.case-badge-escalated { background: rgba(248,113,113,0.15); color: var(--accent-red); }

/* ── Confidence Bar ──────────────────────────────────────── */
.case-confidence-bar {
    width: 100%;
    height: 6px;
    background: var(--bg-secondary);
    border-radius: 3px;
    overflow: hidden;
    margin-top: 4px;
}
.case-confidence-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.3s ease;
}

/* ── Field Rows ──────────────────────────────────────────── */
.case-field-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 0.35rem 0;
    border-bottom: 1px solid rgba(42,45,62,0.5);
    gap: 1rem;
}
.case-field-row:last-child {
    border-bottom: none;
}
.case-field-label {
    font-size: 0.78rem;
    color: var(--text-secondary);
    flex-shrink: 0;
    min-width: 110px;
}
.case-field-value {
    font-size: 0.85rem;
    color: var(--text-primary);
    text-align: right;
    word-break: break-word;
}

/* ── Timeline ────────────────────────────────────────────── */
.case-timeline-event {
    display: flex;
    gap: 0.8rem;
    padding: 0.6rem 0;
    border-bottom: 1px solid rgba(42,45,62,0.4);
}
.case-timeline-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-top: 5px;
    flex-shrink: 0;
}
.case-timeline-body {
    flex: 1;
    min-width: 0;
}
.case-timeline-type {
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--text-primary);
}
.case-timeline-meta {
    font-size: 0.72rem;
    color: var(--text-muted);
    margin-top: 1px;
}
.case-timeline-details {
    font-size: 0.78rem;
    color: var(--text-secondary);
    margin-top: 3px;
}

/* ── Utility ─────────────────────────────────────────────── */
.case-arrow-down {
    text-align: center;
    color: var(--text-muted);
    font-size: 1.4rem;
    padding: 0.3rem 0;
    letter-spacing: 0.1em;
}
.case-empty-state {
    text-align: center;
    padding: 3rem 1rem;
    color: var(--text-muted);
}
.case-page-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 0.2rem;
}
.case-page-subtitle {
    font-size: 0.85rem;
    color: var(--text-secondary);
    margin-bottom: 1.2rem;
}
</style>
"""


def inject_global_css() -> None:
    import streamlit as st

    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def metric_card(label: str, value: str, icon: str, color: str = "#4f8cf7") -> str:
    return f"""
    <div class="case-metric-card">
        <div class="case-metric-icon" style="background:{color}22; color:{color};">{icon}</div>
        <div class="case-metric-body">
            <div class="case-metric-value">{value}</div>
            <div class="case-metric-label">{label}</div>
        </div>
    </div>
    """


def confidence_bar_html(score: float) -> str:
    if score >= 0.7:
        color = "#34d399"
    elif score >= 0.4:
        color = "#fbbf24"
    else:
        color = "#f87171"
    pct = max(0.0, min(1.0, score)) * 100
    return f"""
    <div class="case-confidence-bar">
        <div class="case-confidence-fill" style="width:{pct:.0f}%; background:{color};"></div>
    </div>
    """


def risk_badge_class(level: str) -> str:
    mapping = {
        "LOW": "case-badge-low",
        "MEDIUM": "case-badge-medium",
        "HIGH": "case-badge-high",
        "CRITICAL": "case-badge-critical",
    }
    return mapping.get(level.upper(), "case-badge-low")


def lifecycle_badge_class(lifecycle: str) -> str:
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
        "auto_approve": "#34d399",
        "approve": "#34d399",
        "human_review": "#fbbf24",
        "reject": "#f87171",
        "escalate": "#f87171",
        "modify": "#a78bfa",
    }
    return mapping.get(action, "#4f8cf7")


def event_type_color(event_type: str) -> str:
    if "approve" in event_type.lower():
        return "#34d399"
    if "reject" in event_type.lower():
        return "#f87171"
    if "modify" in event_type.lower():
        return "#a78bfa"
    if "escalat" in event_type.lower():
        return "#fb923c"
    if "review" in event_type.lower():
        return "#fbbf24"
    return "#4f8cf7"
