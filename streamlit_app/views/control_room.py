from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any

import httpx
import plotly.graph_objects as go
import streamlit as st

from streamlit_app.components.state import get_client
from streamlit_app.i18n import t
from streamlit_app.ui.components import render_backend_offline

_STATUS_CSS = """
<style>
.case-cr-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 1rem;
  margin-bottom: 1rem;
}
.case-cr-title {
  font-size: 2rem;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.1;
}
.case-cr-subtitle {
  font-size: 0.92rem;
  color: var(--text-secondary);
  margin-top: 0.35rem;
}
.case-cr-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--bg-surface);
  font-size: 0.75rem;
  color: var(--text-secondary);
  white-space: nowrap;
}
.case-cr-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #1a7a4a;
}
.case-kpi {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1rem 1.1rem;
  min-height: 104px;
}
.case-kpi-label {
  font-size: 0.74rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-secondary);
  margin-bottom: 0.45rem;
}
.case-kpi-value {
  font-size: 1.8rem;
  font-weight: 800;
  color: var(--text-primary);
  line-height: 1.1;
}
.case-kpi-note {
  font-size: 0.78rem;
  color: var(--text-secondary);
  margin-top: 0.35rem;
}
.case-panel {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1rem 1rem 0.5rem;
  margin-bottom: 1rem;
}
.case-panel-title {
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-secondary);
  margin-bottom: 0.2rem;
}
.case-empty {
  padding: 1rem 0.2rem 1.2rem;
  color: var(--text-secondary);
  font-size: 0.9rem;
}
.case-queue-item {
  border: 1px solid var(--border);
  border-left: 3px solid #a06800;
  border-radius: 8px;
  padding: 0.75rem 0.9rem;
  margin-bottom: 0.6rem;
  background: var(--bg-surface);
}
.case-queue-title {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--text-primary);
}
.case-queue-meta {
  font-size: 0.78rem;
  color: var(--text-secondary);
  margin-top: 0.2rem;
}
</style>
"""

_COLORS = {
    "auto": "#1a7a4a",
    "human": "#a06800",
    "escalated": "#b82e2e",
    "rejected": "#6b7280",
    "modified": "#6a3fb5",
    "neutral": "#1a7a7a",
}


def _check_url(url: str, timeout: float = 3.0, headers: dict[str, str] | None = None) -> bool:
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url, headers=headers or {})
            return resp.status_code == 200
    except Exception:
        return False


def _status_badge(is_online: bool) -> str:
    color = "#1a7a4a" if is_online else "#b82e2e"
    label = t("room_online") if is_online else t("room_offline_status")
    return (
        f'<span class="case-cr-chip"><span class="case-cr-dot" style="background:{color}"></span>'
        f"{label}</span>"
    )


def _kpi(label: str, value: str, note: str = "") -> str:
    note_html = f'<div class="case-kpi-note">{note}</div>' if note else ""
    return (
        '<div class="case-kpi">'
        f'<div class="case-kpi-label">{label}</div>'
        f'<div class="case-kpi-value">{value}</div>'
        f"{note_html}"
        "</div>"
    )


def _decision_route(decision: dict[str, Any]) -> str:
    lifecycle = str(decision.get("lifecycle", "")).lower()
    has_override = decision.get("human_override") is not None
    if lifecycle == "approved" and not has_override:
        return "auto"
    if lifecycle in {"under_review", "pending"}:
        return "human"
    if lifecycle == "escalated":
        return "escalated"
    if lifecycle == "rejected":
        return "rejected"
    if lifecycle == "modified":
        return "modified"
    return "human"


def _route_label(route: str) -> str:
    mapping = {
        "auto": t("room_kpi_auto"),
        "human": t("room_kpi_hitl"),
        "escalated": t("room_kpi_escalated"),
        "rejected": t("room_rejected"),
        "modified": t("room_modified"),
    }
    return mapping.get(route, route)


def _apply_filters(
    decisions: list[dict[str, Any]],
    domain: str,
    provider: str,
    lifecycle: str,
    time_range: str,
) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    max_age_hours: float | None = None
    if time_range == t("room_range_24h"):
        max_age_hours = 24
    elif time_range == t("room_range_7d"):
        max_age_hours = 24 * 7
    elif time_range == t("room_range_30d"):
        max_age_hours = 24 * 30

    filtered: list[dict[str, Any]] = []
    for d in decisions:
        if domain != t("room_filter_all") and d.get("domain") != domain:
            continue
        d_provider = str((d.get("metadata") or {}).get("provider", "mock")).lower()
        if provider != t("room_filter_all") and d_provider != provider.lower():
            continue
        if lifecycle != t("room_filter_all") and d.get("lifecycle") != lifecycle:
            continue
        if max_age_hours is not None:
            dt = _parse_created_at(str(d.get("created_at", "")))
            if dt is None:
                continue
            age_hours = (now - dt).total_seconds() / 3600
            if age_hours > max_age_hours:
                continue
        filtered.append(d)
    return filtered


def _plot_layout(title: str) -> dict[str, Any]:
    return {
        "title": {"text": title, "font": {"size": 13, "color": "#334155"}},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "margin": {"l": 24, "r": 16, "t": 44, "b": 24},
        "legend": {"orientation": "h", "y": -0.15},
        "font": {"family": "Inter, sans-serif", "color": "#475569"},
    }


def _routing_chart(decisions: list[dict[str, Any]]) -> go.Figure:
    counts: dict[str, int] = {"auto": 0, "human": 0, "escalated": 0, "rejected": 0, "modified": 0}
    for d in decisions:
        counts[_decision_route(d)] += 1
    labels = [_route_label(k) for k, v in counts.items() if v > 0]
    values = [v for v in counts.values() if v > 0]
    colors = [_COLORS[k] for k, v in counts.items() if v > 0]
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.62,
                marker={"colors": colors, "line": {"color": "#ffffff", "width": 2}},
                textinfo="label+percent",
                hovertemplate="%{label}: %{value}<extra></extra>",
            )
        ]
    )
    fig.update_layout(**_plot_layout(t("room_chart_routing")), showlegend=False)
    return fig


def _domain_chart(decisions: list[dict[str, Any]]) -> go.Figure:
    by_domain: dict[str, int] = {}
    for d in decisions:
        domain = str(d.get("domain", "unknown"))
        by_domain[domain] = by_domain.get(domain, 0) + 1
    domains = sorted(by_domain.keys())
    values = [by_domain[d] for d in domains]
    fig = go.Figure(
        data=[
            go.Bar(
                x=domains,
                y=values,
                marker_color="#1a7a7a",
                hovertemplate="%{x}: %{y}<extra></extra>",
            )
        ]
    )
    layout = _plot_layout(t("room_chart_domains"))
    layout["xaxis"] = {"tickangle": -20, "gridcolor": "rgba(148,163,184,0.15)"}
    layout["yaxis"] = {"gridcolor": "rgba(148,163,184,0.15)", "dtick": 1}
    fig.update_layout(**layout)
    return fig


def _outcome_chart(decisions: list[dict[str, Any]]) -> go.Figure:
    by_route: dict[str, int] = {}
    for d in decisions:
        route = _decision_route(d)
        by_route[route] = by_route.get(route, 0) + 1
    order = ["auto", "human", "escalated", "rejected", "modified"]
    labels = [_route_label(r) for r in order if by_route.get(r, 0) > 0]
    values = [by_route[r] for r in order if by_route.get(r, 0) > 0]
    colors = [_COLORS[r] for r in order if by_route.get(r, 0) > 0]
    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=values,
                marker_color=colors,
                hovertemplate="%{x}: %{y}<extra></extra>",
            )
        ]
    )
    layout = _plot_layout(t("room_chart_reliability"))
    layout["yaxis"] = {"gridcolor": "rgba(148,163,184,0.15)", "dtick": 1}
    layout["xaxis"] = {"gridcolor": "rgba(148,163,184,0.08)"}
    fig.update_layout(**layout)
    return fig


def _latency_chart(decisions: list[dict[str, Any]]) -> go.Figure:
    latencies = [float(d.get("processing_time_ms", 0) or 0) for d in decisions]
    latencies = [v for v in latencies if v > 0]
    fig = go.Figure(data=[go.Histogram(x=latencies, nbinsx=12, marker_color="#475569")])
    layout = _plot_layout(t("room_kpi_latency"))
    layout["xaxis"] = {"title": "ms", "gridcolor": "rgba(148,163,184,0.15)"}
    layout["yaxis"] = {"title": "count", "gridcolor": "rgba(148,163,184,0.15)", "dtick": 1}
    fig.update_layout(**layout)
    return fig


def _parse_created_at(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _timeline_chart(decisions: list[dict[str, Any]]) -> go.Figure:
    buckets: dict[str, int] = {}
    for d in decisions:
        dt = _parse_created_at(str(d.get("created_at", "")))
        if dt is None:
            continue
        key = dt.strftime("%Y-%m-%d %H:00")
        buckets[key] = buckets.get(key, 0) + 1
    keys = sorted(buckets.keys())
    values = [buckets[k] for k in keys]
    fig = go.Figure(
        data=[
            go.Scatter(
                x=keys,
                y=values,
                mode="lines+markers",
                line={"color": "#1a7a7a", "width": 3},
                marker={"size": 6},
                hovertemplate="%{x}: %{y}<extra></extra>",
            )
        ]
    )
    layout = _plot_layout(t("room_chart_timeline"))
    layout["xaxis"] = {"gridcolor": "rgba(148,163,184,0.15)"}
    layout["yaxis"] = {"gridcolor": "rgba(148,163,184,0.15)", "dtick": 1}
    fig.update_layout(**layout)
    return fig


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    vals = sorted(values)
    k = (len(vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(vals) - 1)
    if f == c:
        return vals[f]
    return vals[f] + (vals[c] - vals[f]) * (k - f)


def _provider_metrics(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_provider: dict[str, dict[str, Any]] = {}
    for d in decisions:
        meta = d.get("metadata") or {}
        pinfo = meta.get("provider_info") or {}
        provider = str(pinfo.get("provider") or meta.get("provider") or "mock")
        entry = by_provider.setdefault(
            provider,
            {"provider": provider, "count": 0, "latencies": [], "tokens": 0, "cost": 0.0, "errors": 0},
        )
        entry["count"] += 1
        latency = float(pinfo.get("latency_ms") or 0)
        if latency > 0:
            entry["latencies"].append(latency)
        entry["tokens"] += int(pinfo.get("total_tokens") or 0)
        cost = meta.get("cost") or {}
        entry["cost"] += float(cost.get("total_cost") or 0)
        if d.get("error"):
            entry["errors"] += 1
    rows = []
    for provider, entry in by_provider.items():
        latencies = entry["latencies"]
        rows.append(
            {
                "provider": provider,
                "cases": entry["count"],
                "p50_ms": round(_percentile(latencies, 0.50), 1),
                "p95_ms": round(_percentile(latencies, 0.95), 1),
                "tokens": entry["tokens"],
                "cost_usd": round(entry["cost"], 6),
                "errors": entry["errors"],
            }
        )
    return sorted(rows, key=lambda r: r["provider"])


def _validation_chart(decisions: list[dict[str, Any]]) -> go.Figure:
    stages = ["parse", "schema", "semantic", "domain"]
    totals = dict.fromkeys(stages, 0)
    for d in decisions:
        rel = (d.get("metadata") or {}).get("reliability") or {}
        sf = rel.get("stage_failures") or {}
        for s in stages:
            totals[s] += int(sf.get(s, 0) or 0)
    fig = go.Figure(
        data=[
            go.Bar(
                x=[s.upper() for s in stages],
                y=[totals[s] for s in stages],
                marker_color=["#475569", "#b82e2e", "#a06800", "#1a7a7a"],
                hovertemplate="%{x}: %{y}<extra></extra>",
            )
        ]
    )
    layout = _plot_layout(t("room_chart_validation"))
    layout["yaxis"] = {"gridcolor": "rgba(148,163,184,0.15)", "dtick": 1}
    fig.update_layout(**layout)
    return fig


def _trend_chart(decisions: list[dict[str, Any]], metric: str) -> go.Figure:
    buckets: dict[str, list[float]] = {}
    for d in decisions:
        dt = _parse_created_at(str(d.get("created_at", "")))
        if dt is None:
            continue
        key = dt.strftime("%Y-%m-%d %H:00") if len({str(x.get("created_at", ""))[:10] for x in decisions if x.get("created_at")}) <= 2 else dt.strftime("%Y-%m-%d")
        val: float | None = None
        if metric == "latency":
            v = float(d.get("processing_time_ms", 0) or 0)
            val = v if v > 0 else None
        elif metric == "cost":
            meta = d.get("metadata") or {}
            cost_obj = meta.get("cost") or {}
            c = meta.get("cost_usd", meta.get("estimated_cost_usd"))
            if c is None and isinstance(cost_obj, dict):
                c = cost_obj.get("total_usd", cost_obj.get("estimated_cost_usd"))
            try:
                val = float(c) if c is not None else None
            except Exception:
                val = None
        if val is not None:
            buckets.setdefault(key, []).append(val)
    if not buckets:
        fig = go.Figure()
        fig.update_layout(height=220, margin={"l": 20, "r": 20, "t": 20, "b": 20})
        return fig
    labels = sorted(buckets.keys())
    if metric == "latency":
        y = []
        for k in labels:
            vals = sorted(buckets[k])
            idx = max(int(0.95 * len(vals)) - 1, 0)
            y.append(vals[idx])
        name = "p95 latency ms"
    else:
        y = [sum(buckets[k]) for k in labels]
        name = "Total cost USD"
    fig = go.Figure(go.Scatter(x=labels, y=y, mode="lines+markers", name=name, line={"color": "#2d6fa3" if metric == "latency" else "#1a7a4a"}))
    fig.update_layout(height=220, margin={"l": 20, "r": 20, "t": 20, "b": 20}, xaxis_title=None, yaxis_title=name)
    return fig


def render() -> None:
    st.markdown(_STATUS_CSS, unsafe_allow_html=True)
    client = get_client()

    try:
        health = client.health_sync()
        api_ok = health.get("status") in ("ok", "degraded")
    except Exception:
        api_ok = False
        health = {}

    if not api_ok:
        render_backend_offline()
        return

    refresh_options = ["Off", "30s", "60s"]
    st.session_state.setdefault("room_auto_refresh", "Off")
    if st.session_state["room_auto_refresh"] not in refresh_options:
        st.session_state["room_auto_refresh"] = "Off"
    refresh_map = {"Off": None, "30s": 30, "60s": 60}
    run_every = refresh_map.get(st.session_state.get("room_auto_refresh", "Off"))

    def _body() -> None:

        decisions_resp: dict[str, Any] = {}
        try:
            decisions_resp = client.list_cases_sync(limit=200, offset=0)
        except Exception:
            decisions_resp = {}
        decisions = decisions_resp.get("decisions", []) if isinstance(decisions_resp, dict) else []

        provider_data: dict[str, Any] = {}
        try:
            provider_data = client.list_providers_sync()
        except Exception:
            provider_data = {}
        active_provider = str(provider_data.get("active_provider", "mock"))

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        st.markdown(
            '<div class="case-cr-header">'
            f'<div><div class="case-cr-title">{t("room_title")}</div>'
            f'<div class="case-cr-subtitle">{t("room_subtitle")}</div></div>'
            f"{_status_badge(api_ok)}"
            "</div>",
            unsafe_allow_html=True,
        )

        db_status = str(health.get("database", health.get("db_status", "unknown")))
        provider_name = str(health.get("provider", health.get("default_provider", active_provider)))
        mode = "MOCK" if "mock" in provider_name.lower() else "REAL"
        h1, h2, h3, h4 = st.columns(4)
        with h1:
            st.markdown(f'<div class="case-cr-chip">API · {"online" if api_ok else "offline"}</div>', unsafe_allow_html=True)
        with h2:
            st.markdown(f'<div class="case-cr-chip">DB · {db_status}</div>', unsafe_allow_html=True)
        with h3:
            st.markdown(f'<div class="case-cr-chip">Provider · {provider_name} · {mode}</div>', unsafe_allow_html=True)
        with h4:
            st.markdown(f'<div class="case-cr-chip">Version · {health.get("version", "n/a")}</div>', unsafe_allow_html=True)

        domains = sorted({str(d.get("domain", "")) for d in decisions if d.get("domain")})
        providers = sorted(
            {str((d.get("metadata") or {}).get("provider", "mock")).lower() for d in decisions}
            or {active_provider.lower()}
        )
        lifecycles = sorted({str(d.get("lifecycle", "")) for d in decisions if d.get("lifecycle")})

        domain_options = [t("room_filter_all"), *domains]
        provider_options = [t("room_filter_all"), *providers]
        lifecycle_options = [t("room_filter_all"), *lifecycles]
        range_options = [t("room_filter_all"), t("room_range_24h"), t("room_range_7d"), t("room_range_30d")]
        for key, options in (
            ("room_domain_filter", domain_options),
            ("room_provider_filter", provider_options),
            ("room_lifecycle_filter", lifecycle_options),
            ("room_time_range", range_options),
        ):
            st.session_state.setdefault(key, options[0])
            if st.session_state[key] not in options:
                st.session_state[key] = options[0]

        f1, f2, f3, f4, f5, f6 = st.columns([1, 1, 1, 1, 1.2, 0.7])
        with f1:
            time_range = st.selectbox(t("room_filter_range"), range_options, key="room_time_range")
        with f2:
            domain_filter = st.selectbox(t("room_filter_domain"), domain_options, key="room_domain_filter")
        with f3:
            provider_filter = st.selectbox(t("room_filter_provider"), provider_options, key="room_provider_filter")
        with f4:
            lifecycle_filter = st.selectbox(t("room_filter_lifecycle"), lifecycle_options, key="room_lifecycle_filter")
        with f5:
            st.selectbox(
                t("room_auto_refresh"),
                ["Off", "30s", "60s"],
                key="room_auto_refresh",
            )
            st.caption(f"{t('room_last_refresh')}: {now}")
        with f6:
            if st.button(t("room_refresh"), use_container_width=True):
                st.rerun()

        filtered = _apply_filters(decisions, domain_filter, provider_filter, lifecycle_filter, time_range)

        total = len(filtered)
        route_counts = {"auto": 0, "human": 0, "escalated": 0}
        errors = 0
        latencies: list[float] = []
        for d in filtered:
            route = _decision_route(d)
            if route in route_counts:
                route_counts[route] += 1
            if d.get("error"):
                errors += 1
            ms = float(d.get("processing_time_ms", 0) or 0)
            if ms > 0:
                latencies.append(ms)
        avg_latency = f"{sum(latencies) / len(latencies):.0f} ms" if latencies else "—"
        def _rate(n: int) -> str:
            return f"{(n / total * 100):.0f}%" if total else "—"

        k1, k2, k3, k4, k5, k6 = st.columns(6)
        with k1:
            st.markdown(_kpi(t("room_kpi_total"), str(total)), unsafe_allow_html=True)
        with k2:
            st.markdown(_kpi(t("room_kpi_auto_rate"), _rate(route_counts["auto"]), f"{route_counts['auto']}"), unsafe_allow_html=True)
        with k3:
            st.markdown(_kpi(t("room_kpi_hitl_rate"), _rate(route_counts["human"]), f"{route_counts['human']}"), unsafe_allow_html=True)
        with k4:
            st.markdown(_kpi(t("room_kpi_escalated_rate"), _rate(route_counts["escalated"]), f"{route_counts['escalated']}"), unsafe_allow_html=True)
        with k5:
            st.markdown(_kpi(t("room_kpi_error_rate"), _rate(errors), f"{errors}"), unsafe_allow_html=True)
        with k6:
            st.markdown(_kpi(t("room_kpi_latency"), avg_latency), unsafe_allow_html=True)

        if not filtered:
            st.markdown(
                f'<div class="case-panel"><div class="case-empty">{t("room_no_data")}</div></div>',
                unsafe_allow_html=True,
            )
            return

        c1, c2 = st.columns([1, 1.2])
        with c1:
            st.markdown('<div class="case-panel">', unsafe_allow_html=True)
            st.plotly_chart(_routing_chart(filtered), use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="case-panel">', unsafe_allow_html=True)
            st.plotly_chart(_domain_chart(filtered), use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

        c3, c4 = st.columns([1.2, 1])
        with c3:
            st.markdown('<div class="case-panel">', unsafe_allow_html=True)
            st.plotly_chart(_outcome_chart(filtered), use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)
        with c4:
            st.markdown('<div class="case-panel">', unsafe_allow_html=True)
            if latencies:
                st.plotly_chart(
                    _latency_chart(filtered), use_container_width=True, config={"displayModeBar": False}
                )
            else:
                st.markdown(f'<div class="case-empty">{t("room_no_data")}</div>', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        timeline_has_data = any(_parse_created_at(str(d.get("created_at", ""))) for d in filtered)
        if timeline_has_data:
            st.markdown('<div class="case-panel">', unsafe_allow_html=True)
            st.plotly_chart(_timeline_chart(filtered), use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

        provider_rows = _provider_metrics(filtered)
        pcol, vcol = st.columns([1.3, 1])
        with pcol:
            st.markdown(
                f'<div class="case-panel"><div class="case-panel-title">{t("room_section_providers")}</div>',
                unsafe_allow_html=True,
            )
            if provider_rows:
                st.dataframe(provider_rows, use_container_width=True, hide_index=True)
            else:
                st.markdown(f'<div class="case-empty">{t("room_no_data")}</div>', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with vcol:
            st.markdown('<div class="case-panel">', unsafe_allow_html=True)
            st.plotly_chart(_validation_chart(filtered), use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

        tcol, ccol = st.columns(2)
        with tcol:
            st.markdown('<div class="case-panel"><div class="case-panel-title">{t("room_chart_latency_trend")}</div>', unsafe_allow_html=True)
            st.plotly_chart(_trend_chart(filtered, "latency"), use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)
        with ccol:
            st.markdown('<div class="case-panel"><div class="case-panel-title">Cost trend (USD)</div>', unsafe_allow_html=True)
            st.plotly_chart(_trend_chart(filtered, "cost"), use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            f'<div class="case-panel"><div class="case-panel-title">{t("room_queue_title")}</div>',
            unsafe_allow_html=True,
        )
        queue = [d for d in filtered if d.get("lifecycle") in {"under_review", "escalated", "pending"}]
        if not queue:
            st.markdown(f'<div class="case-empty">{t("room_queue_empty")}</div>', unsafe_allow_html=True)
        else:
            def _age_hours(decision: dict[str, Any]) -> float | None:
                dt = _parse_created_at(str(decision.get("created_at", "")))
                if dt is None:
                    return None
                return max((datetime.now(timezone.utc) - dt).total_seconds() / 3600, 0.0)

            queue = sorted(queue, key=lambda d: (_age_hours(d) is None, -(_age_hours(d) or 0)))
            for idx, d in enumerate(queue[:8]):
                case_id = str(d.get("case_id", "?"))
                domain = str(d.get("domain", "?"))
                lifecycle = str(d.get("lifecycle", "?"))
                action = str(d.get("action", "?"))
                confidence = float(d.get("confidence", 0) or 0)
                age_h = _age_hours(d)
                if age_h is None:
                    age_label = "—"
                    border = "#a06800"
                elif age_h >= 24:
                    age_label = f"{age_h / 24:.1f}d"
                    border = "#b82e2e"
                else:
                    age_label = f"{age_h:.1f}h"
                    border = "#a06800"
                urgency = str(d.get("urgency") or (d.get("metadata") or {}).get("urgency") or "—")
                c_q1, c_q2, c_q3 = st.columns([4.2, 1, 1])
                with c_q1:
                    st.markdown(
                        f'<div class="case-queue-item" style="border-left-color:{border};">'
                        f'<div class="case-queue-title">{case_id} · {action} · {urgency}</div>'
                        f'<div class="case-queue-meta">{domain} · {lifecycle} · confidence {confidence:.0%} · {t("room_queue_age")}: {age_label}</div>'
                        "</div>",
                        unsafe_allow_html=True,
                    )
                with c_q2:
                    if st.button(t("room_open_cases"), key=f"room_q_cases_{case_id}_{idx}", use_container_width=True):
                        st.session_state["selected_case_id"] = case_id
                        st.session_state["current_page"] = "cases"
                        st.rerun()
                with c_q3:
                    if st.button(t("room_open_review"), key=f"room_open_{case_id}_{idx}", use_container_width=True):
                        st.session_state["current_page"] = "human_review"
                        st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            f'<div class="case-panel"><div class="case-panel-title">{t("room_section_recent")}</div>',
            unsafe_allow_html=True,
        )
        table_rows = []
        for d in filtered[:20]:
            table_rows.append(
                {
                    "case_id": d.get("case_id"),
                    "domain": d.get("domain"),
                    "lifecycle": d.get("lifecycle"),
                    "action": d.get("action"),
                    "confidence": round(float(d.get("confidence", 0) or 0), 3),
                    "processing_time_ms": round(float(d.get("processing_time_ms", 0) or 0), 1),
                    "provider": str((d.get("metadata") or {}).get("provider", "mock")),
                    "created_at": d.get("created_at", ""),
                }
            )
        st.dataframe(table_rows, use_container_width=True, hide_index=True)
        if table_rows:
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=list(table_rows[0].keys()))
            writer.writeheader()
            writer.writerows(table_rows)
            st.download_button(
                "CSV",
                data=buf.getvalue(),
                file_name="case_control_room.csv",
                mime="text/csv",
                use_container_width=False,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        case_ids = [str(d.get("case_id")) for d in filtered if d.get("case_id")]
        if case_ids:
            st.markdown(
                '<div class="case-panel"><div class="case-panel-title">Case drill-down</div>',
                unsafe_allow_html=True,
            )
            sc1, sc2, sc3 = st.columns([3, 1, 1])
            with sc1:
                selected_case = st.selectbox("Case", case_ids, key="room_case_drilldown")
            with sc2:
                if st.button(t("room_open_cases"), key="room_nav_cases", use_container_width=True):
                    st.session_state["selected_case_id"] = st.session_state.get("room_case_drilldown")
                    st.session_state["current_page"] = "cases"
                    st.rerun()
            with sc3:
                if st.button(t("room_open_review"), key="room_nav_review", use_container_width=True):
                    st.session_state["current_page"] = "human_review"
                    st.rerun()
            if selected_case:
                try:
                    case_data = client.get_case_sync(selected_case)
                except Exception:
                    case_data = {"error": True}
                if case_data.get("error"):
                    st.markdown(f'<div class="case-empty">{t("room_no_data")}</div>', unsafe_allow_html=True)
                else:
                    decision = case_data.get("decision", {})
                    d1, d2, d3, d4 = st.columns(4)
                    d1.metric("Lifecycle", str(decision.get("lifecycle", "?")))
                    d2.metric("Confidence", f"{float(decision.get('confidence', 0) or 0):.0%}")
                    d3.metric("Action", str(decision.get("action", "?")))
                    d4.metric("Latency ms", f"{float(decision.get('processing_time_ms', 0) or 0):.0f}")
                    st.write(str(decision.get("reason", "")))
                    meta = decision.get("metadata") or {}
                    provider = str(meta.get("provider", "mock"))
                    model = str(meta.get("model", meta.get("model_id", "n/a")))
                    mode = "MOCK" if "mock" in provider.lower() else "REAL"
                    tokens = meta.get("total_tokens", meta.get("tokens"))
                    cost = meta.get("cost_usd", meta.get("estimated_cost_usd"))
                    info_parts = [f"Provider: {provider} ({mode})", f"Model: {model}"]
                    if tokens is not None:
                        info_parts.append(f"Tokens: {tokens}")
                    if cost is not None:
                        try:
                            info_parts.append(f"Cost: ${float(cost):.5f}")
                        except Exception:
                            info_parts.append(f"Cost: {cost}")
                    st.caption(" · ".join(info_parts))
                    events = case_data.get("audit_events", [])
                    if events:
                        st.dataframe(
                            [
                                {
                                    "timestamp": e.get("timestamp"),
                                    "event_type": e.get("event_type"),
                                    "actor": e.get("actor"),
                                    "details": str(e.get("details", ""))[:120],
                                }
                                for e in events
                            ],
                            use_container_width=True,
                            hide_index=True,
                        )
            st.markdown("</div>", unsafe_allow_html=True)

    if run_every:
        st.fragment(_body, run_every=run_every)()
    else:
        _body()
