"""Home, inventory, and emission-factor views."""

from __future__ import annotations

import requests
import streamlit as st

from src.ui.api_client import API_BASE_URL, api_post, show_api_error
from src.ui.components.charts import plot_emission_pie, plot_quota_comparison
from src.ui.navigation import navigate_to
from src.ui.theme import empty_state, notice, page_header


VEHICLE_TYPES = [
    "重型柴油货车",
    "中型柴油货车",
    "轻型柴油货车",
    "微型汽油货车",
    "LNG重型货车",
    "新能源物流车",
]


def render_home() -> None:
    page_header(
        "项目总览",
        "把车队数据转化为可复核的减排判断",
        "从排放基线开始，比较减排情景，再将核算结果与政策依据整理为报告。",
    )

    fleet = st.session_state.get("fleet_data", [])
    result = st.session_state.get("carbon_result")
    report_path = st.session_state.get("report_path")

    m1, m2, m3 = st.columns(3)
    m1.metric("车队记录", f"{len(fleet)} 组", help="已录入的车型配置数量")
    m2.metric(
        "最近核算",
        f"{result.get('total_emission_t', 0):,.0f} tCO2e" if result else "待计算",
        help="车辆直接运营排放",
    )
    m3.metric("报告状态", "已生成" if report_path else "未生成")

    st.markdown("## 建议工作流")
    st.markdown(
        """
        <div class="workflow-strip" role="list" aria-label="项目分析流程">
            <div class="workflow-step" role="listitem">
                <span class="workflow-step__number">01</span>
                <strong>建立排放基线</strong>
                <span>录入车型、数量、里程和满载率，形成可复核盘点。</span>
            </div>
            <div class="workflow-step" role="listitem">
                <span class="workflow-step__number">02</span>
                <strong>比较减排情景</strong>
                <span>调整新能源替换与满载率，查看排放和成本变化。</span>
            </div>
            <div class="workflow-step" role="listitem">
                <span class="workflow-step__number">03</span>
                <strong>整理依据并导出</strong>
                <span>检索政策资料，将核算口径、结果和建议写入报告。</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    c1.button(
        "开始排放盘点",
        type="primary",
        width="stretch",
        on_click=navigate_to,
        args=("排放盘点",),
    )
    c2.button(
        "进入减排分析",
        width="stretch",
        disabled=not bool(result),
        on_click=navigate_to,
        args=("减排分析",),
    )
    c3.button(
        "查看报告导出",
        width="stretch",
        disabled=not bool(result),
        on_click=navigate_to,
        args=("报告导出",),
    )

    notice(
        "科研原型边界",
        "物流运输行业目前未纳入全国碳市场配额管理。模拟碳预算用于方案比较，不代表法定配额、履约义务或可交易资产。",
        amber=True,
    )


def render_inventory() -> None:
    page_header(
        "核算 · 第一步",
        "车队直接运营排放盘点",
        "录入年度车队活动数据，计算分车型排放、模拟碳预算差额和碳价对标情景。",
    )
    st.session_state.setdefault("fleet_data", [])

    company_name = st.text_input(
        "企业名称",
        value=st.session_state.get("company_name", "示例物流公司"),
        key="inventory_company",
    )
    scenario_reduction_target_pct = st.slider(
        "模拟预算减排目标",
        min_value=0,
        max_value=50,
        value=int(round(float(st.session_state.get("scenario_reduction_target", 0.10)) * 100)),
        step=5,
        format="%d%%",
        help="相对各车型参考活动排放的科研情景参数，不是政策目标或法定配额。",
    )
    scenario_reduction_target = scenario_reduction_target_pct / 100

    st.markdown("## 添加车队记录")
    with st.form("fleet_entry", clear_on_submit=False):
        c1, c2 = st.columns(2)
        vehicle_type = c1.selectbox("车型", VEHICLE_TYPES)
        count = c2.number_input("车辆数量（辆）", min_value=1, value=50, step=1)
        c3, c4 = st.columns(2)
        annual_km = c3.number_input("单车年均里程（km）", min_value=1000, value=80000, step=1000)
        load_factor_pct = c4.slider("平均满载率", 0, 100, 75, 5, format="%d%%")
        add_vehicle = st.form_submit_button("添加到车队", type="primary")

    if add_vehicle:
        st.session_state.fleet_data.append(
            {
                "vehicle_type": vehicle_type,
                "count": int(count),
                "annual_km": int(annual_km),
                "load_factor": load_factor_pct / 100,
            }
        )
        st.session_state.pop("carbon_result", None)
        st.session_state.pop("reduction_result", None)
        st.session_state.pop("report_path", None)
        st.rerun()

    fleet = st.session_state.fleet_data
    st.markdown("## 当前车队")
    if fleet:
        rows = [
            {
                "序号": index + 1,
                "车型": item["vehicle_type"],
                "车辆数": item["count"],
                "年均里程（km）": f"{item['annual_km']:,}",
                "满载率": f"{item['load_factor']:.0%}",
            }
            for index, item in enumerate(fleet)
        ]
        st.dataframe(rows, width="stretch", hide_index=True)

        d1, d2 = st.columns([3, 1])
        selected_row = d1.selectbox(
            "需要删除的记录",
            range(len(fleet)),
            format_func=lambda i: f"{i + 1}. {fleet[i]['vehicle_type']} · {fleet[i]['count']} 辆",
        )
        if d2.button("删除所选", width="stretch"):
            fleet.pop(selected_row)
            st.session_state.pop("carbon_result", None)
            st.session_state.pop("reduction_result", None)
            st.session_state.pop("report_path", None)
            st.rerun()

        if st.button("计算排放基线", type="primary", width="stretch"):
            if not company_name.strip():
                st.error("请填写企业名称后再计算。")
            else:
                _calculate_inventory(company_name, scenario_reduction_target)
    else:
        empty_state("尚未添加车队记录", "先填写上方四项活动数据并添加记录，至少需要一组车型才能计算。")

    result = st.session_state.get("carbon_result")
    if result:
        _render_inventory_result(result)


def _calculate_inventory(company_name: str, reduction_target: float) -> None:
    with st.spinner("正在核算车队排放…"):
        try:
            response = api_post(
                "/api/calculate",
                {
                    "company_name": company_name.strip(),
                    "fleet": st.session_state.fleet_data,
                    "scenario_reduction_target": reduction_target,
                },
            )
            if response.status_code != 200:
                show_api_error(response)
                return
            st.session_state.carbon_result = response.json()
            st.session_state.company_name = company_name.strip()
            st.session_state.scenario_reduction_target = reduction_target
            st.session_state.pop("reduction_result", None)
            st.session_state.pop("report_path", None)
        except requests.RequestException as exc:
            st.error(f"无法连接核算服务（{API_BASE_URL}）：{exc}")


def _render_inventory_result(result: dict) -> None:
    budget = result.get("carbon_budget", {})
    gap = budget.get("预算差额_t", 0)
    status = budget.get("状态", "未知")

    st.divider()
    st.markdown("## 核算结果")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("直接运营排放", f"{result.get('total_emission_t', 0):,.0f} tCO2e")
    m2.metric("模拟碳预算", f"{budget.get('模拟碳预算_t', 0):,.0f} tCO2e")
    m3.metric("预算差额", f"{gap:+,.0f} tCO2e")
    m4.metric("情景状态", status)

    chart_left, chart_right = st.columns([1, 1.25])
    with chart_left:
        st.plotly_chart(
            plot_emission_pie(result.get("emission_by_type", {})),
            width="stretch",
            config={"displayModeBar": False, "responsive": True},
        )
    with chart_right:
        st.plotly_chart(
            plot_quota_comparison(
                result.get("total_emission_t", 0),
                budget.get("模拟碳预算_t", 0),
                gap,
            ),
            width="stretch",
            config={"displayModeBar": False, "responsive": True},
        )

    st.markdown("### 分车型明细")
    emission_rows = [
        {"车型": name, **details}
        for name, details in result.get("emission_by_type", {}).items()
    ]
    st.dataframe(emission_rows, width="stretch", hide_index=True)

    st.markdown("### 碳价对标情景")
    cost = result.get("scenario_cost", {})
    if cost.get("情景成本_参考价") is not None:
        cost_rows = [
            {"项目": "参考碳价", "数值": f"{cost.get('当前碳价_元每吨', 0):,.2f} 元/tCO2e"},
            {"项目": "情景成本参考值", "数值": f"{cost.get('情景成本_参考价', 0):,.0f} 元"},
            {
                "项目": "情景成本区间",
                "数值": (
                    f"{cost.get('情景成本区间_low', 0):,.0f} – "
                    f"{cost.get('情景成本区间_high', 0):,.0f} 元"
                ),
            },
        ]
    else:
        cost_rows = [
            {"项目": "情景判断", "数值": cost.get("情景判断", status)},
            {"项目": "预算结余", "数值": f"{cost.get('预算结余_t', abs(gap)):,.0f} tCO2e"},
            {
                "项目": "对标潜在价值区间",
                "数值": f"{cost.get('潜在价值_low', 0):,.0f} – {cost.get('潜在价值_high', 0):,.0f} 元",
            },
        ]
    st.table(cost_rows)
    notice("口径提示", cost.get("备注", result.get("methodology_note", "科研情景估算，仅供方案比较。")), amber=True)


def render_factors() -> None:
    page_header(
        "方法与数据",
        "排放因子参考表",
        "查看当前模型使用的车型排放因子、活动水平参考值和数据来源。",
    )
    from src.engine.emission_factors import get_all_factors

    factors = get_all_factors()
    rows = [
        {
            "车型": name,
            "燃料类型": data["fuel_type"],
            "CO2 排放因子（kg/km）": data["co2_kg_per_km"],
            "油耗参考（L/100km）": data.get("fuel_consumption_l_per_100km") or "不适用",
            "年均里程参考（km）": f"{data['avg_annual_km']:,}",
        }
        for name, data in factors.items()
    ]
    st.dataframe(rows, width="stretch", hide_index=True)

    st.markdown("## 数据来源")
    for name, data in factors.items():
        with st.expander(name):
            st.write(data["source"])
    notice(
        "使用建议",
        "参考因子适合科研原型和前期情景比较。企业正式盘查应优先使用可追溯的燃料消耗、里程和采购台账。",
    )
