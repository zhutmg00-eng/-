"""Streamlit 主入口"""
import streamlit as st

st.set_page_config(
    page_title="碳资产管理与合规决策助手",
    page_icon="🌿",
    layout="wide",
)

st.title("🌿 碳资产管理与合规决策助手")
st.caption("面向物流运输企业 · 碳排放基线测算 + 碳交易政策智能顾问")

page = st.sidebar.radio(
    "功能导航",
    ["🏠 首页", "📊 碳资产盘点", "💬 政策顾问", "📋 排放因子表", "📄 生成报告"],
)

if page == "🏠 首页":
    st.markdown("""
    ### 欢迎使用碳资产管理助手

    本工具帮助物流运输企业完成三个核心任务：

    1. **碳资产盘点** — 输入你的车队数据，自动计算碳排放基线
    2. **配额缺口估算** — 对照碳市场规则，计算你的碳配额缺口
    3. **政策智能顾问** — 用自然语言提问，AI帮你解读最新碳交易法规

    **开始使用**：点击左侧"📊 碳资产盘点"输入你的车队数据
    """)

elif page == "📊 碳资产盘点":
    st.header("📊 碳资产盘点")
    st.write("输入车队数据，自动计算碳排放基线、配额缺口和合规成本")

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
            import requests
            with st.spinner("计算中..."):
                try:
                    response = requests.post("http://localhost:8000/api/calculate", json={
                        "company_name": company_name,
                        "fleet": st.session_state.fleet_data,
                    })
                    if response.status_code == 200:
                        result = response.json()
                        st.session_state.carbon_result = result

                        m1, m2, m3 = st.columns(3)
                        m1.metric("年度碳排放", f"{result['total_emission_t']:.0f} tCO₂")
                        m2.metric("配额缺口", f"{result['quota_gap']['缺口_t']:.0f} tCO₂")
                        m3.metric("缺口状态", result['quota_gap']['状态'])

                        st.subheader("分车型排放明细")
                        st.dataframe(result['emission_by_type'])

                        st.subheader("合规成本估算")
                        st.json(result['compliance_cost'])
                    else:
                        st.error(f"API错误: {response.status_code}")
                except requests.ConnectionError:
                    st.error("无法连接后端API，请确保FastAPI服务正在运行 (uvicorn src.api.main:app --port 8000)")
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
                import requests
                carbon_profile = st.session_state.get("carbon_result", {})
                try:
                    response = requests.post("http://localhost:8000/api/ask", json={
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
                        st.error(f"API错误: {response.status_code}")
                except requests.ConnectionError:
                    st.error("无法连接后端API，请确保FastAPI服务正在运行")

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
    st.header("📄 合规报告导出")
    result = st.session_state.get("carbon_result")
    if result:
        st.write("当前计算结果已缓存，可导出为PDF报告")
        st.json(result)
        if st.button("📥 导出PDF报告"):
            st.info("PDF导出功能开发中，请手动保存上方数据")
    else:
        st.info("请先在'碳资产盘点'页面进行计算")
