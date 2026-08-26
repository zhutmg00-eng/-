"""Streamlit 主入口"""
import os
from pathlib import Path

import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
APP_API_KEY = os.getenv("APP_API_KEY", "")
API_HEADERS = {"X-API-Key": APP_API_KEY} if APP_API_KEY else {}


def api_post(path: str, payload: dict) -> requests.Response:
    """调用后端 API，并避免请求无限等待。"""
    return requests.post(
        f"{API_BASE_URL}{path}",
        json=payload,
        headers=API_HEADERS,
        timeout=30,
    )


def show_api_error(response: requests.Response) -> None:
    """向页面展示后端返回的可读错误。"""
    try:
        detail = response.json().get("detail", response.text)
    except ValueError:
        detail = response.text
    st.error(f"API 请求失败 ({response.status_code}): {detail}")


st.set_page_config(
    page_title="物流碳排放与减排情景决策助手",
    page_icon="🌿",
    layout="wide",
)

st.title("🌿 物流碳排放与减排情景决策助手")
st.caption("面向物流运输企业 · 直接运营排放核算 + 减排情景分析 + 政策检索")

page = st.sidebar.radio(
    "功能导航",
    ["🏠 首页", "📊 碳排放盘点", "💬 政策顾问", "📋 排放因子表", "📄 生成报告", "🔬 减排分析"],
)

if page == "🏠 首页":
    st.markdown("""
    ### 物流碳排放科研原型

    本工具支持物流运输企业开展三类分析：

    1. **直接运营排放盘点** — 根据车型、里程和满载率测算年度排放基线
    2. **模拟碳预算情景** — 用原型基准比较预算差额及碳价对标成本
    3. **政策资料检索** — 用自然语言检索知识库中的政策依据

    > 科研原型说明：物流运输行业目前未纳入全国碳市场配额管理，模拟预算不代表法定配额、履约义务或可交易资产。新能源车当前仅按直接运营排放为零核算，未计购电间接排放与车辆全生命周期排放。
    """)

elif page == "📊 碳排放盘点":
    st.header("📊 碳排放盘点")
    st.write("输入车队数据，计算直接运营排放、模拟碳预算差额和情景成本")
    st.caption("核算边界：新能源车仅计直接运营排放，未计购电间接排放和全生命周期排放。")

    company_name = st.text_input("企业名称", "示例物流公司")

    st.subheader("车队信息")
    if "fleet_data" not in st.session_state:
        st.session_state.fleet_data = []

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        vehicle_type = st.selectbox(
            "车型",
            ["重型柴油货车", "中型柴油货车", "轻型柴油货车", "微型汽油货车", "LNG重型货车", "新能源物流车"]
        )
    with col2:
        count = st.number_input("数量（辆）", min_value=1, value=50)
    with col3:
        annual_km = st.number_input("年均里程(km)", min_value=1000, value=80000, step=1000)
    with col4:
        load_factor = st.slider("满载率", 0.0, 1.0, 0.75, 0.05)
    with col5:
        if st.button("➕ 添加"):
            st.session_state.fleet_data.append({
                "vehicle_type": vehicle_type,
                "count": count,
                "annual_km": annual_km,
                "load_factor": load_factor,
            })
            st.rerun()

    # 显示已添加的车队
    if st.session_state.fleet_data:
        st.write("**已添加的车型：**")
        for i, item in enumerate(st.session_state.fleet_data):
            cols = st.columns([2, 1, 2, 1, 1])
            cols[0].write(item["vehicle_type"])
            cols[1].write(f"{item['count']}辆")
            cols[2].write(f"{item['annual_km']:.0f}km")
            cols[3].write(f"{item['load_factor']:.0%}")
            if cols[4].button("删除", key=f"del_{i}"):
                st.session_state.fleet_data.pop(i)
                st.rerun()

        if st.button("⚡ 计算碳排放", type="primary"):
            with st.spinner("计算中..."):
                try:
                    response = api_post("/api/calculate", {
                        "company_name": company_name,
                        "fleet": st.session_state.fleet_data,
                    })
                    if response.status_code == 200:
                        result = response.json()
                        st.session_state.carbon_result = result
                        st.session_state.company_name = company_name.strip()

                        m1, m2, m3 = st.columns(3)
                        m1.metric("直接运营排放", f"{result['total_emission_t']:.0f} tCO2e")
                        m2.metric("模拟预算差额", f"{result['carbon_budget']['预算差额_t']:.0f} tCO2e")
                        m3.metric("情景状态", result['carbon_budget']['状态'])

                        st.subheader("分车型排放明细")
                        emission_rows = [
                            {"车型": name, **details}
                            for name, details in result["emission_by_type"].items()
                        ]
                        st.dataframe(emission_rows, use_container_width=True, hide_index=True)

                        st.subheader("碳价对标情景")
                        st.json(result['scenario_cost'])
                    else:
                        show_api_error(response)
                except requests.RequestException as exc:
                    st.error(f"无法连接后端 API ({API_BASE_URL}): {exc}")
    else:
        st.info("请添加至少一种车型")

elif page == "💬 政策顾问":
    st.header("💬 碳交易政策智能顾问")
    st.caption("我是您的AI碳政策顾问，请用自然语言向我提问")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("请输入您的碳交易合规问题..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("正在检索相关政策..."):
                carbon_profile = st.session_state.get("carbon_result", {})
                try:
                    response = api_post("/api/ask", {
                        "question": prompt,
                        "carbon_profile": carbon_profile,
                    })
                    if response.status_code == 200:
                        result = response.json()
                        answer = result['answer']
                        st.markdown(answer)
                        with st.expander("📚 参考政策来源"):
                            for src in result['retrieved_sources']:
                                st.write(f"- {src['source']} ({src['date']})")
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                    else:
                        show_api_error(response)
                except requests.RequestException as exc:
                    st.error(f"无法连接后端 API ({API_BASE_URL}): {exc}")

elif page == "📋 排放因子表":
    st.header("📋 排放因子参考表")
    from src.engine.emission_factors import get_all_factors
    factors = get_all_factors()
    for name, data in factors.items():
        with st.expander(f"{name} ({data['fuel_type']})"):
            st.write(f"- CO₂排放因子: **{data['co2_kg_per_km']} kg/km**")
            if data.get('fuel_consumption_l_per_100km'):
                st.write(f"- 油耗参考: {data['fuel_consumption_l_per_100km']} L/100km")
            st.write(f"- 年均里程参考: {data['avg_annual_km']:,} km")
            st.write(f"- 数据来源: {data['source']}")

elif page == "📄 生成报告":
    st.header("📄 情景报告导出")
    result = st.session_state.get("carbon_result")
    if result:
        st.write("当前计算结果已缓存，可导出为PDF报告")
        st.json(result)
        if st.button("📥 导出PDF报告", type="primary"):
            try:
                from src.ui.components.report import generate_carbon_report
                company_name = st.session_state.get("company_name", "示例物流公司")
                emission_by_type = result.get("emission_by_type", {})
                total_emission = result.get("total_emission_t", 0)
                total_vehicles = result.get("total_vehicles", 0)
                carbon_budget = result.get("carbon_budget", {})
                scenario_cost = result.get("scenario_cost", {})

                # 获取政策顾问的 llm_answer（如果存在）
                llm_answer = ""
                if "messages" in st.session_state:
                    for msg in st.session_state.messages:
                        if msg["role"] == "assistant":
                            llm_answer = msg["content"]  # 取最近一条

                report_path = generate_carbon_report(
                    company_name=company_name,
                    total_emission_t=total_emission,
                    total_vehicles=total_vehicles,
                    emission_by_type=emission_by_type,
                    total_quota_t=carbon_budget.get("模拟碳预算_t", 0),
                    gap_t=carbon_budget.get("预算差额_t", 0),
                    gap_status=carbon_budget.get("状态", "未知"),
                    compliance_cost=scenario_cost,
                    llm_answer=llm_answer,
                )
                st.success(f"✅ 报告已保存：`{report_path}`")
                st.write(f"**报告路径：** `{report_path}`")

                # PDF 下载按钮
                with open(report_path, "rb") as f:
                    pdf_bytes = f.read()
                st.download_button(
                    label="📥 下载 PDF 报告",
                    data=pdf_bytes,
                    file_name=Path(report_path).name,
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"生成报告失败：{e}")
    else:
        st.info("请先在'碳排放盘点'页面进行计算")

# ============================================================
# 🔬 减排分析
# ============================================================
elif page == "🔬 减排分析":
    st.header("🔬 减排情景分析")
    st.caption("模拟不同减排措施对直接运营排放和碳预算差额的影响")

    carbon_result = st.session_state.get("carbon_result")
    fleet_data = st.session_state.get("fleet_data", [])

    if not carbon_result or not fleet_data:
        st.info("请先在'碳排放盘点'页面添加车型并计算排放量")
    else:
        # 显示基线
        total_emission = carbon_result.get("total_emission_t", 0)
        total_vehicles = carbon_result.get("total_vehicles", 0)
        carbon_budget = carbon_result.get("carbon_budget", {})
        scenario_cost = carbon_result.get("scenario_cost", {})

        st.subheader("📊 当前排放基线")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("直接运营排放", f"{total_emission:,.0f} tCO2e")
        col2.metric("总车辆数", f"{total_vehicles} 辆")
        col3.metric("模拟预算差额", f"{carbon_budget.get('预算差额_t', 0):,.0f} tCO2e")
        col4.metric("情景状态", carbon_budget.get("状态", "未知"))

        st.divider()

        # 减排措施配置
        st.subheader("⚙️ 减排措施配置")

        # 选择车型和减排方式
        vehicle_types = list(carbon_result.get("emission_by_type", {}).keys())
        selected_type = st.selectbox("选择车型", vehicle_types)

        # 获取该车型的车辆数
        type_info = carbon_result.get("emission_by_type", {}).get(selected_type, {})
        type_count = type_info.get("车辆数", 0)
        type_emission = type_info.get("排放量_tCO2", 0)
        ef = type_info.get("排放因子_kg_per_km", 0)

        col_a, col_b = st.columns(2)
        with col_a:
            replace_count = st.slider(
                "替换为新能源车数量",
                min_value=0,
                max_value=int(type_count),
                value=0,
                step=1,
            )
        with col_b:
            replace_load = st.slider(
                "提升满载率车辆数",
                min_value=0,
                max_value=int(type_count),
                value=0,
                step=1,
            )

        # 满载率目标
        current_load = 0.75
        if fleet_data:
            for fd in fleet_data:
                if fd["vehicle_type"] == selected_type:
                    current_load = fd.get("load_factor", 0.75)
                    break

        target_load = st.slider(
            "目标满载率",
            min_value=0.50,
            max_value=1.00,
            value=max(current_load, 0.80),
            step=0.05,
            help="提升满载率可降低满载率调整系数，减少排放",)

        st.divider()

        # 计算减排效果
        if st.button("🚀 计算减排效果", type="primary"):
            with st.spinner("正在计算减排情景..."):
                try:
                    # 尝试导入 reduction 模块
                    try:
                        from src.engine.calculator import VehicleGroupData, calculate_emission
                        from src.engine.quota import estimate_quota_gap
                        from src.engine.carbon_price import estimate_compliance_cost, load_carbon_price_data
                        from src.engine import reduction as reduction_module
                        use_engine = True
                    except ImportError:
                        use_engine = False

                    if use_engine:
                        # 构建基线车队
                        baseline_fleet = []
                        for fd in fleet_data:
                            baseline_fleet.append(VehicleGroupData(
                                vehicle_type=fd["vehicle_type"],
                                count=fd["count"],
                                annual_km=fd["annual_km"],
                                load_factor=fd["load_factor"],
                            ))

                        # 构建减排措施
                        changes = {}
                        if replace_count > 0:
                            changes["替换为新能源物流车"] = replace_count
                        if replace_load > 0:
                            changes[f"提升满载率至{target_load}"] = replace_load

                        if changes:
                            scenario_result = reduction_module.analyze_reduction_scenario(
                                baseline_fleet=baseline_fleet,
                                changes=changes,
                            )
                            scenario_dict = scenario_result.to_dict()
                        else:
                            scenario_dict = {
                                "baseline_emission": total_emission,
                                "scenario_emission": total_emission,
                                "reduction_t": 0,
                                "reduction_pct": 0,
                                "cost_savings": {},
                                "recommendations": ["请配置减排措施后重新计算"],
                            }
                    else:
                        # 回退：基于排放因子直接计算
                        from src.engine.emission_factors import get_emission_factor

                        baseline_emission = total_emission
                        reduction = 0.0

                        if replace_count > 0 and ef > 0:
                            # 替换为新能源：减排量 = 车辆数 × 年均里程 × 排放因子 / 1000
                            # 获取该车种的年均里程
                            avg_km = fd.get("annual_km", 80000) if fleet_data else 80000
                            # 查找该车型的年均里程
                            for f in fleet_data:
                                if f["vehicle_type"] == selected_type:
                                    avg_km = f["annual_km"]
                                    break
                            reduction += replace_count * avg_km * ef / 1000

                        if replace_load > 0 and current_load < target_load:
                            # 提升满载率带来的减排
                            from src.engine.calculator import calculate_load_adjustment
                            old_adj = calculate_load_adjustment(current_load)
                            new_adj = calculate_load_adjustment(target_load)
                            # 获取年均里程
                            avg_km = 80000
                            for f in fleet_data:
                                if f["vehicle_type"] == selected_type:
                                    avg_km = f["annual_km"]
                                    break
                            load_reduction = replace_count * avg_km * ef * (old_adj - new_adj) / 1000
                            reduction += max(0, load_reduction)

                        scenario_emission = max(0, baseline_emission - reduction)
                        reduction_pct = round(reduction / baseline_emission * 100, 2) if baseline_emission > 0 else 0

                        # 估算成本节省
                        current_cost = scenario_cost.get("情景成本_参考价", 0)
                        saved_cost = round(current_cost * (reduction_pct / 100), 2) if current_cost > 0 and reduction_pct > 0 else 0

                        scenario_dict = {
                            "baseline_emission": round(baseline_emission, 2),
                            "scenario_emission": round(scenario_emission, 2),
                            "reduction_t": round(reduction, 2),
                            "reduction_pct": reduction_pct,
                            "cost_savings": {
                                "基线情景成本_元": current_cost,
                                "情景成本_元": round(current_cost - saved_cost, 2),
                                "节省_元": saved_cost,
                            },
                            "recommendations": [
                                f"替换 {replace_count} 辆{selected_type}为新能源车，直接运营减排 {reduction:,.0f} tCO2e（未计购电间接排放）",
                            ] + ([
                                f"提升 {replace_load} 辆{selected_type}满载率从{current_load:.0%}至{target_load:.0%}，额外减排 {max(0,load_reduction):,.0f} tCO2e",
                            ] if replace_load > 0 and current_load < target_load else []),
                        }

                    # 展示结果
                    st.subheader("📈 减排情景结果")
                    r = scenario_dict

                    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                    col_r1.metric("情景直接排放", f"{r.get('scenario_emission', 0):,.0f} tCO2e")
                    col_r2.metric("直接减排量", f"{r.get('reduction_t', 0):,.0f} tCO2e")
                    col_r3.metric("减排比例", f"{r.get('reduction_pct', 0):.1f}%")
                    col_r4.metric("成本节省", f"{r.get('cost_savings', {}).get('节省_元', 0):,.0f} 元")

                    st.divider()
                    st.subheader("💡 减排建议")
                    for rec in r.get("recommendations", []):
                        st.write(rec)

                except Exception as e:
                    st.error(f"计算减排效果失败：{e}")
                    import traceback
                    st.code(traceback.format_exc())
