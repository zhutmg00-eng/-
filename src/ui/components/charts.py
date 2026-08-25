from __future__ import annotations

"""碳资产助手可视化组件

提供基于 plotly 的图表绘制函数，用于展示碳排放分析结果。
"""

import plotly.graph_objects as go
from typing import Dict, List, Optional

# 绿色系配色（环形图/多系列）
GREEN_PALETTE = [
    "#1b5e20", "#2e7d32", "#388e3c", "#43a047",
    "#4caf50", "#66bb6a", "#81c784", "#a5d6a7",
]

# 中文字典映射
TYPE_LABELS: Dict[str, str] = {
    "重型柴油货车": "重型柴油货车",
    "中型柴油货车": "中型柴油货车",
    "轻型柴油货车": "轻型柴油货车",
    "微型汽油货车": "微型汽油货车",
    "LNG重型货车": "LNG重型货车",
    "新能源物流车": "新能源物流车",
}


# ---------------------------------------------------------------------------
# 1. 排放占比环形图
# ---------------------------------------------------------------------------

def plot_emission_pie(emission_by_type: dict) -> go.Figure:
    """绘制各车型碳排放占比的环形图。

    Args:
        emission_by_type: 排放分类数据 dict，key 为车型名称，
            value 包含 ``"排放量_tCO2"`` 键（见 ``CarbonBaselineResult.emission_by_type``）。

    Returns:
        plotly 环形图 figure。
    """
    labels = []
    values = []
    for vtype, info in emission_by_type.items():
        labels.append(TYPE_LABELS.get(vtype, vtype))
        values.append(info.get("排放量_tCO2", 0))

    fig = go.Figure(data=[
        go.Pie(
            labels=labels,
            values=values,
            hole=0.55,
            marker=dict(colors=GREEN_PALETTE),
            textposition="inside",
            textinfo="percent",
            hoverinfo="label+value+percent",
        )
    ])

    fig.update_layout(
        title={
            "text": "🚛 各车型碳排放占比",
            "y": 0.95,
            "x": 0.5,
            "xanchor": "center",
            "yanchor": "top",
        },
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        height=420,
        margin=dict(l=20, r=20, t=60, b=20),
    )
    fig.update_traces(textinfo="percent", hovertemplate="%{label}<br>%{value:.2f} tCO₂<br>%{percent:.1f}")
    return fig


# ---------------------------------------------------------------------------
# 2. 配额对比柱状图
# ---------------------------------------------------------------------------

def plot_quota_comparison(total_emission: float, total_quota: float, gap: float) -> go.Figure:
    """绘制企业排放量、配额总量与缺口的对比柱状图。

    Args:
        total_emission: 企业年度碳排放总量 (tCO₂)。
        total_quota: 企业免费配额总量 (tCO₂)。
        gap: 配额缺口（正 = 需购买，负 = 盈余）。

    Returns:
        plotly 柱状图 figure。
    """
    labels = ["排放量", "配额总量", "缺口"]
    values = [total_emission, total_quota, gap]
    colors = ["#388e3c", "#1565c0"]
    # 缺口用红色高亮：正缺口(需购买)为红色，负缺口(盈余)为橙色
    if gap >= 0:
        colors.append("#d32f2f")  # 缺口红色
    else:
        colors.append("#f57c00")  # 盈余橙色

    fig = go.Figure(data=[
        go.Bar(
            x=labels,
            y=values,
            marker_color=colors,
            text=[
                f"{total_emission:,.1f}",
                f"{total_quota:,.1f}",
                f"{gap:+,.1f}",
            ],
            textposition="outside",
            textfont=dict(size=14),
        )
    ])

    fig.update_layout(
        title={
            "text": "📊 碳排放与配额对比",
            "y": 0.95,
            "x": 0.5,
            "xanchor": "center",
            "yanchor": "top",
        },
        yaxis_title="tCO₂",
        xaxis_tickfont=dict(size=12),
        height=400,
        margin=dict(l=20, r=20, t=60, b=50),
        shapes=[
            dict(
                type="line",
                x0=-0.5, x1=2.5,
                y0=0, y1=0,
                line=dict(color="black", width=1.2),
            )
        ],
    )
    fig.update_yaxes(showgrid=True, gridwidth=0.5, gridcolor="lightgray")
    return fig


# ---------------------------------------------------------------------------
# 3. 碳价统计水平线对比图
# ---------------------------------------------------------------------------

def plot_carbon_price_stats(price_stats: dict) -> go.Figure | None:
    """绘制碳价统计水平线对比图。

    展示当前碳价、90 日均价、90 日最高/最低价之间的相对位置关系。

    Args:
        price_stats: 碳价统计 dict，需包含以下键：
            ``"当前价"``, ``"近90日均价"``, ``"近90日最高"``, ``"近90日最低"``。

    Returns:
        plotly 水平线 figure；如果输入为空或无有效数据则返回 ``None``。
    """
    if not price_stats:
        return None

    current = price_stats.get("当前价")
    avg = price_stats.get("近90日均价")
    high = price_stats.get("近90日最高")
    low = price_stats.get("近90日最低")

    # 至少需要当前价和均价才算有效数据
    if current is None and avg is None:
        return None

    # 确定 y 轴范围
    all_vals = [v for v in [low, current, avg, high] if v is not None]
    if not all_vals:
        return None

    y_min = min(all_vals) * 0.9
    y_max = max(all_vals) * 1.1

    fig = go.Figure()

    lines = []
    annotations = []

    # 当前价 — 绿色
    if current is not None:
        lines.append(("current", current, "#2e7d32", f"当前价: ¥{current}"))
    # 90日均价 — 蓝色
    if avg is not None:
        lines.append(("avg", avg, "#1565c0", f"90日均价: ¥{avg}"))
    # 最高价 — 红色
    if high is not None:
        lines.append(("high", high, "#d32f2f", f"90日最高: ¥{high}"))
    # 最低价 — 橙色
    if low is not None:
        lines.append(("low", low, "#f57c00", f"90日最低: ¥{low}"))

    for key, val, color, label in lines:
        fig.add_hline(
            y=val,
            line=dict(color=color, width=1.5, dash="dot"),
            annotation_text=label,
            annotation_position="top right",
            annotation_font=dict(size=11, color=color),
        )
        annotations.append((key, val, color))

    fig.update_layout(
        title={
            "text": "📈 碳价统计对比",
            "y": 0.95,
            "x": 0.5,
            "xanchor": "center",
            "yanchor": "top",
        },
        yaxis_title="价格 (元/吨CO₂)",
        yaxis=dict(range=[y_min, y_max], showgrid=True, gridwidth=0.5, gridcolor="lightgray"),
        xaxis=dict(visible=False),
        height=380,
        margin=dict(l=60, r=40, t=60, b=40),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )

    # 在左侧 y 轴添加标签
    for key, val, color in annotations:
        fig.add_annotation(
            xref="paper", yref="y",
            x=-0.02, y=val,
            text=f"{val}",
            showarrow=False,
            font=dict(size=11, color=color),
            align="right",
        )

    return fig


# ---------------------------------------------------------------------------
# 4. 多企业车队对比
# ---------------------------------------------------------------------------

def plot_fleet_comparison(multi_results: List[dict]) -> go.Figure:
    """绘制多企业碳排放、配额与缺口的分组对比柱状图。

    Args:
        multi_results: 每个企业的结果 dict，格式：

            .. code-block:: python

                {
                    "company_name": "A企业",
                    "total_emission_t": 1234,
                    "total_quota_t": 1000,
                    "gap_t": 234,
                    ...
                }

    Returns:
        plotly 分组柱状图 figure。
    """
    if not multi_results:
        fig = go.Figure()
        fig.update_layout(title="多企业对比", height=300)
        return fig

    companies = [r.get("company_name", "未知") for r in multi_results]
    emissions = [r.get("total_emission_t", 0) for r in multi_results]
    quotas = [r.get("total_quota_t", 0) for r in multi_results]
    gaps = [r.get("gap_t", 0) for r in multi_results]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name="排放量",
        x=companies,
        y=emissions,
        marker_color="#388e3c",
        text=[f"{v:,.0f}" for v in emissions],
        textposition="outside",
        textfont=dict(size=11),
    ))
    fig.add_trace(go.Bar(
        name="配额总量",
        x=companies,
        y=quotas,
        marker_color="#1565c0",
        text=[f"{v:,.0f}" for v in quotas],
        textposition="outside",
        textfont=dict(size=11),
    ))
    fig.add_trace(go.Bar(
        name="缺口",
        x=companies,
        y=gaps,
        marker_color=["#d32f2f" if g > 0 else "#f57c00" for g in gaps],
        text=[f"{v:+,.0f}" for v in gaps],
        textposition="outside",
        textfont=dict(size=11),
    ))

    fig.update_layout(
        title={
            "text": "🏭 多企业碳排放与配额对比",
            "y": 0.95,
            "x": 0.5,
            "xanchor": "center",
            "yanchor": "top",
        },
        barmode="group",
        yaxis_title="tCO₂",
        height=420,
        margin=dict(l=20, r=20, t=60, b=80),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        xaxis=dict(tickangle=0),
        shapes=[
            dict(
                type="line", x0=-0.5, x1=len(companies) - 0.5,
                y0=0, y1=0,
                line=dict(color="black", width=1.2),
            )
        ],
    )
    fig.update_yaxes(showgrid=True, gridwidth=0.5, gridcolor="lightgray")

    return fig
