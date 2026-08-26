"""Plotly charts used across the carbon-analysis interface."""

from __future__ import annotations

from typing import Dict, List

import plotly.graph_objects as go


INK = "#17231d"
MUTED = "#66756d"
GRID = "#dfe6e2"
GREEN = "#1f6a4a"
GREEN_DARK = "#155239"
TEAL = "#39766c"
AMBER = "#b27425"
RED = "#a83a35"
GRAY = "#8a9891"
CATEGORY_PALETTE = [GREEN, AMBER, TEAL, "#728078", "#4f6259", "#d0a35b"]

TYPE_LABELS: Dict[str, str] = {
    "重型柴油货车": "重型柴油货车",
    "中型柴油货车": "中型柴油货车",
    "轻型柴油货车": "轻型柴油货车",
    "微型汽油货车": "微型汽油货车",
    "LNG重型货车": "LNG重型货车",
    "新能源物流车": "新能源物流车",
}


def _apply_layout(fig: go.Figure, *, title: str, height: int = 400) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=16, color=INK)),
        height=height,
        margin=dict(l=20, r=20, t=58, b=35),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI, Microsoft YaHei, sans-serif", color=INK, size=12),
        hoverlabel=dict(bgcolor="#ffffff", bordercolor=GRID, font=dict(color=INK)),
    )
    return fig


def plot_emission_pie(emission_by_type: dict) -> go.Figure:
    """Show each vehicle type's share of direct operating emissions."""
    labels = [TYPE_LABELS.get(name, name) for name in emission_by_type]
    values = [details.get("排放量_tCO2", 0) for details in emission_by_type.values()]
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.62,
                marker=dict(colors=CATEGORY_PALETTE, line=dict(color="#ffffff", width=2)),
                textposition="inside",
                textinfo="percent",
                sort=False,
                hovertemplate="%{label}<br>%{value:,.2f} tCO2e<br>占比 %{percent}<extra></extra>",
            )
        ]
    )
    _apply_layout(fig, title="车型排放构成", height=390)
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="left", x=0),
        margin=dict(l=10, r=10, t=58, b=80),
    )
    return fig


def plot_quota_comparison(total_emission: float, total_quota: float, gap: float) -> go.Figure:
    """Compare direct emissions with the simulated carbon budget."""
    labels = ["直接运营排放", "模拟碳预算", "预算差额"]
    values = [total_emission, total_quota, gap]
    gap_color = RED if gap > 0 else TEAL
    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=values,
                marker_color=[GREEN, GRAY, gap_color],
                text=[f"{total_emission:,.1f}", f"{total_quota:,.1f}", f"{gap:+,.1f}"],
                textposition="outside",
                cliponaxis=False,
                hovertemplate="%{x}<br>%{y:,.2f} tCO2e<extra></extra>",
            )
        ]
    )
    _apply_layout(fig, title="排放与模拟预算", height=390)
    fig.update_layout(yaxis_title="tCO2e", showlegend=False)
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=True, zerolinecolor=MUTED)
    fig.update_xaxes(showgrid=False)
    return fig


def plot_reduction_comparison(baseline: float, scenario: float) -> go.Figure:
    """Compare baseline and post-measure direct operating emissions."""
    reduction = max(0.0, baseline - scenario)
    fig = go.Figure(
        data=[
            go.Bar(
                y=["基线", "减排情景"],
                x=[baseline, scenario],
                orientation="h",
                marker_color=[GRAY, GREEN],
                text=[f"{baseline:,.1f} tCO2e", f"{scenario:,.1f} tCO2e"],
                textposition="outside",
                cliponaxis=False,
                hovertemplate="%{y}<br>%{x:,.2f} tCO2e<extra></extra>",
            )
        ]
    )
    _apply_layout(fig, title=f"情景前后对比 · 减少 {reduction:,.1f} tCO2e", height=320)
    fig.update_layout(xaxis_title="tCO2e", showlegend=False, margin=dict(l=20, r=90, t=58, b=40))
    fig.update_xaxes(showgrid=True, gridcolor=GRID, rangemode="tozero")
    fig.update_yaxes(autorange="reversed")
    return fig


def plot_carbon_price_stats(price_stats: dict) -> go.Figure | None:
    """Show current and recent carbon-price reference points."""
    if not price_stats:
        return None
    points = [
        ("当前价", price_stats.get("当前价"), GREEN),
        ("90 日均价", price_stats.get("近90日均价"), GRAY),
        ("90 日最高", price_stats.get("近90日最高"), RED),
        ("90 日最低", price_stats.get("近90日最低"), AMBER),
    ]
    points = [(label, value, color) for label, value, color in points if value is not None]
    if not points:
        return None

    fig = go.Figure()
    for label, value, color in points:
        fig.add_trace(
            go.Scatter(
                x=[0, 1],
                y=[value, value],
                mode="lines",
                name=f"{label} · {value:.2f} 元",
                line=dict(color=color, width=2, dash="dot" if label != "当前价" else "solid"),
                hovertemplate=f"{label}<br>{value:.2f} 元/tCO2e<extra></extra>",
            )
        )
    _apply_layout(fig, title="碳价参考区间", height=360)
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis_title="元/tCO2e",
        legend=dict(orientation="h", yanchor="top", y=-0.08, xanchor="left", x=0),
        margin=dict(l=55, r=20, t=58, b=90),
    )
    fig.update_yaxes(showgrid=True, gridcolor=GRID)
    return fig


def plot_fleet_comparison(multi_results: List[dict]) -> go.Figure:
    """Compare direct emissions, simulated budgets, and gaps by company."""
    if not multi_results:
        fig = go.Figure()
        _apply_layout(fig, title="企业情景对比", height=300)
        fig.add_annotation(
            text="暂无可比较的企业数据",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(color=MUTED),
        )
        return fig

    companies = [item.get("company_name", "未命名企业") for item in multi_results]
    emissions = [item.get("total_emission_t", 0) for item in multi_results]
    budgets = [item.get("carbon_budget_t", item.get("total_quota_t", 0)) for item in multi_results]
    gaps = [item.get("budget_gap_t", item.get("gap_t", 0)) for item in multi_results]
    fig = go.Figure()
    for name, values, color in (
        ("直接运营排放", emissions, GREEN),
        ("模拟碳预算", budgets, GRAY),
    ):
        fig.add_trace(
            go.Bar(
                name=name,
                x=companies,
                y=values,
                marker_color=color,
                text=[f"{value:,.0f}" for value in values],
                textposition="outside",
                hovertemplate=f"%{{x}}<br>{name} %{{y:,.2f}} tCO2e<extra></extra>",
            )
        )
    fig.add_trace(
        go.Bar(
            name="预算差额",
            x=companies,
            y=gaps,
            marker_color=[RED if value > 0 else TEAL for value in gaps],
            text=[f"{value:+,.0f}" for value in gaps],
            textposition="outside",
            hovertemplate="%{x}<br>预算差额 %{y:,.2f} tCO2e<extra></extra>",
        )
    )
    _apply_layout(fig, title="企业情景对比", height=420)
    fig.update_layout(
        barmode="group",
        yaxis_title="tCO2e",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=25, r=20, t=85, b=60),
    )
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=True, zerolinecolor=MUTED)
    return fig
