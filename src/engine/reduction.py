"""减排分析引擎

功能：
- 分析单车队在不同减排情景下的排放变化
- 多情景对比，支持"替换车型"和"提升满载率"等策略
- 在预算约束下寻找最优减排组合

减排策略说明：
- 替换车型：将某一车型替换为更低排放的车型（如柴油→新能源）
- 提升满载率：将满载率从较低水平提升到目标水平
- 混合策略：多种减排手段组合

所有排放计算复用 calculator 引擎，不重复造轮子。
"""
from dataclasses import dataclass, field
from typing import List, Optional
from src.engine.calculator import VehicleGroupData, calculate_emission, calculate_load_adjustment
from src.engine.quota import estimate_quota_gap
from src.engine.carbon_price import estimate_compliance_cost, load_carbon_price_data


# ============================================================
# 减排策略定义
# ============================================================

@dataclass
class ReductionScenario:
    """减排情景

    Attributes:
        name: 情景名称（如"2030新能源化"）
        description: 情景描述
        changes: 减排措施映射 {"措施名称": 涉及车辆数}
                 示例:
                   {"替换为新能源物流车": 10}
                   {"提升满载率至0.8": 30}
                   {"重型货车更换LNG": 5}
    """
    name: str
    description: str
    changes: dict  # {"措施名称": 涉及车辆数}


@dataclass
class ReductionAnalysis:
    """减排分析结果

    Attributes:
        baseline_emission: 基线排放量 (tCO₂)
        scenario_emission: 情景排放量 (tCO₂)
        reduction_t: 减少排放量 (tCO₂)
        reduction_pct: 减排百分比 (%)
        cost_savings: 合规成本节省详情
        recommendations: 具体建议列表
        name: 情景名称（可选）
    """
    baseline_emission: float
    scenario_emission: float
    reduction_t: float
    reduction_pct: float
    cost_savings: dict
    recommendations: list = field(default_factory=list)
    name: str = ""

    def to_dict(self) -> dict:
        """序列化为字典，供API返回"""
        return {
            "name": self.name,
            "baseline_emission": self.baseline_emission,
            "scenario_emission": self.scenario_emission,
            "reduction_t": self.reduction_t,
            "reduction_pct": round(self.reduction_pct, 2),
            "cost_savings": self.cost_savings,
            "recommendations": self.recommendations,
        }


@dataclass
class ScenarioComparison:
    """多情景对比结果"""
    baseline_emission: float
    scenarios: list  # list of ReductionAnalysis
    recommendations: list  # 全局建议


# ============================================================
# 减排措施映射表
# ============================================================

# 车型替换映射：{原车型: (替换车型, 单车减排量_kg_per_km)}
# 单车减排量 = (原排放因子 - 新排放因子) kg/km
REPLACEMENT_MAP = {
    "重型柴油货车": ("新能源物流车", 0.877),      # 0.877 - 0.0 = 0.877
    "中型柴油货车": ("新能源物流车", 0.508),       # 0.508 - 0.0 = 0.508
    "轻型柴油货车": ("新能源物流车", 0.374),       # 0.374 - 0.0 = 0.374
    "微型汽油货车": ("新能源物流车", 0.216),       # 0.216 - 0.0 = 0.216
}

# 各车型年均里程参考（用于计算减排量）
AVG_ANNUAL_KM = {
    "重型柴油货车": 80000,
    "中型柴油货车": 50000,
    "轻型柴油货车": 30000,
    "微型汽油货车": 20000,
    "新能源物流车": 40000,
    "LNG重型货车": 80000,
}


# ============================================================
# 核心函数
# ============================================================

def _build_scenario_fleet(baseline_fleet: List[VehicleGroupData], changes: dict) -> List[VehicleGroupData]:
    """
    根据减排措施构建情景车队

    Args:
        baseline_fleet: 基线车队（VehicleGroupData列表）
        changes: 减排措施 {"措施名称": 涉及车辆数}

    Returns:
        情景车队（VehicleGroupData列表）
    """
    current_fleet = [
        VehicleGroupData(
            vehicle_type=g.vehicle_type,
            count=g.count,
            annual_km=g.annual_km,
            load_factor=g.load_factor,
        )
        for g in baseline_fleet
        if g.count > 0
    ]

    for measure, count in changes.items():
        if count <= 0:
            continue

        if "替换为新能源物流车" in measure or "更换为新能源" in measure or "新能源" in measure:
            remaining_to_replace = count
            new_fleet = []
            for g in current_fleet:
                if remaining_to_replace > 0 and g.vehicle_type != "新能源物流车":
                    replace_num = min(remaining_to_replace, g.count)
                    remaining_to_replace -= replace_num
                    if g.count > replace_num:
                        new_fleet.append(VehicleGroupData(
                            vehicle_type=g.vehicle_type,
                            count=g.count - replace_num,
                            annual_km=g.annual_km,
                            load_factor=g.load_factor,
                        ))
                    new_fleet.append(VehicleGroupData(
                        vehicle_type="新能源物流车",
                        count=replace_num,
                        annual_km=g.annual_km,
                        load_factor=g.load_factor,
                    ))
                else:
                    new_fleet.append(g)
            current_fleet = new_fleet

        elif "更换LNG" in measure or "更换为LNG" in measure or "LNG" in measure:
            remaining_to_replace = count
            new_fleet = []
            for g in current_fleet:
                if remaining_to_replace > 0 and "柴油" in g.vehicle_type:
                    replace_num = min(remaining_to_replace, g.count)
                    remaining_to_replace -= replace_num
                    if g.count > replace_num:
                        new_fleet.append(VehicleGroupData(
                            vehicle_type=g.vehicle_type,
                            count=g.count - replace_num,
                            annual_km=g.annual_km,
                            load_factor=g.load_factor,
                        ))
                    new_fleet.append(VehicleGroupData(
                        vehicle_type="LNG重型货车",
                        count=replace_num,
                        annual_km=g.annual_km,
                        load_factor=g.load_factor,
                    ))
                else:
                    new_fleet.append(g)
            current_fleet = new_fleet

        elif "提升满载率" in measure or "满载率" in measure:
            target_rate = 0.80
            if "至" in measure:
                try:
                    target_rate = float(measure.split("至")[-1].strip().rstrip("%"))
                    if target_rate > 1.0:
                        target_rate /= 100.0
                except ValueError:
                    target_rate = 0.80

            remaining_to_adjust = count
            new_fleet = []
            for g in current_fleet:
                if remaining_to_adjust > 0 and g.load_factor < target_rate:
                    adjust_num = min(remaining_to_adjust, g.count)
                    remaining_to_adjust -= adjust_num
                    if g.count > adjust_num:
                        new_fleet.append(VehicleGroupData(
                            vehicle_type=g.vehicle_type,
                            count=g.count - adjust_num,
                            annual_km=g.annual_km,
                            load_factor=g.load_factor,
                        ))
                    new_fleet.append(VehicleGroupData(
                        vehicle_type=g.vehicle_type,
                        count=adjust_num,
                        annual_km=g.annual_km,
                        load_factor=target_rate,
                    ))
                else:
                    new_fleet.append(g)
            current_fleet = new_fleet

    return [g for g in current_fleet if g.count > 0]


def analyze_reduction_scenario(
    baseline_fleet: List[VehicleGroupData],
    changes: dict,
) -> ReductionAnalysis:
    """
    分析单个减排情景

    Args:
        baseline_fleet: 基线车队
        changes: 减排措施 {"措施名称": 涉及车辆数}

    Returns:
        ReductionAnalysis: 减排分析结果
    """
    # 计算基线排放
    baseline = calculate_emission(baseline_fleet)
    baseline_emission = baseline.total_emission_t

    # 构建情景车队
    scenario_fleet = _build_scenario_fleet(baseline_fleet, changes)

    # 计算情景排放
    if scenario_fleet:
        scenario = calculate_emission(scenario_fleet)
        scenario_emission = scenario.total_emission_t
    else:
        scenario_emission = baseline_emission

    # 计算减排量和百分比
    reduction_t = round(baseline_emission - scenario_emission, 2)
    reduction_pct = round(reduction_t / baseline_emission * 100, 2) if baseline_emission > 0 else 0.0

    # 估算配额缺口变化
    baseline_fleet_summary = {g.vehicle_type: g.count for g in baseline_fleet}
    scenario_fleet_summary = {}
    for g in scenario_fleet:
        scenario_fleet_summary[g.vehicle_type] = scenario_fleet_summary.get(g.vehicle_type, 0) + g.count

    baseline_gap = estimate_quota_gap(baseline_emission, baseline_fleet_summary)
    scenario_gap = estimate_quota_gap(scenario_emission, scenario_fleet_summary)

    # 估算合规成本节省
    price_df = load_carbon_price_data()
    baseline_cost = estimate_compliance_cost(baseline_gap.gap_t, price_df)
    scenario_cost = estimate_compliance_cost(scenario_gap.gap_t, price_df)

    # 计算成本节省
    cost_savings = {}
    if baseline_cost.get("预估合规成本_参考价", 0) > 0 and scenario_cost.get("预估合规成本_参考价", 0) >= 0:
        baseline_cost_val = baseline_cost.get("预估合规成本_参考价", 0)
        scenario_cost_val = scenario_cost.get("预估合规成本_参考价", 0)
        cost_savings = {
            "基线合规成本_元": baseline_cost_val,
            "情景合规成本_元": scenario_cost_val,
            "节省_元": round(baseline_cost_val - scenario_cost_val, 2),
            "配额缺口变化_t": round(baseline_gap.gap_t - scenario_gap.gap_t, 2),
        }
    elif scenario_cost.get("合规需求") == "配额盈余" and baseline_cost.get("合规需求") == "需购买配额":
        # 从缺口变为盈余
        cost_savings = {
            "基线合规成本_元": baseline_cost.get("预估合规成本_参考价", 0),
            "情景合规成本_元": 0,
            "节省_元": round(baseline_cost.get("预估合规成本_参考价", 0), 2),
            "备注": "情景方案使配额从缺口变为盈余",
            "盈余量_t": scenario_cost.get("盈余量_t", 0),
        }

    # 生成建议
    recommendations = _generate_recommendations(baseline_fleet, changes, reduction_t, reduction_pct)

    return ReductionAnalysis(
        baseline_emission=baseline_emission,
        scenario_emission=scenario_emission,
        reduction_t=reduction_t,
        reduction_pct=reduction_pct,
        cost_savings=cost_savings,
        recommendations=recommendations,
    )


def compare_scenarios(
    baseline_fleet: List[VehicleGroupData],
    scenarios: List[ReductionScenario],
) -> ScenarioComparison:
    """
    多情景对比

    Args:
        baseline_fleet: 基线车队
        scenarios: 减排情景列表

    Returns:
        ScenarioComparison: 多情景对比结果
    """
    results = []
    for scenario in scenarios:
        analysis = analyze_reduction_scenario(baseline_fleet, scenario.changes)
        analysis.name = scenario.name  # 附加情景名称
        results.append(analysis)

    # 按减排百分比降序排序
    results.sort(key=lambda x: x.reduction_pct, reverse=True)

    # 全局建议
    global_recommendations = []
    if results:
        best = results[0]
        global_recommendations.append(
            f"最优情景：「{best.name}」，减排{best.reduction_pct}%（{best.reduction_t} tCO₂）"
        )

    # 汇总各情景的减排潜力
    reduction_potentials = [r.reduction_t for r in results]
    max_reduction = max(reduction_potentials) if reduction_potentials else 0
    if max_reduction > 0:
        global_recommendations.append(
            f"所有情景最大可减排{max_reduction} tCO₂"
        )

    # 检查是否有情景能完全覆盖配额缺口
    baseline = calculate_emission(baseline_fleet)
    baseline_summary = {g.vehicle_type: g.count for g in baseline_fleet}
    baseline_gap = estimate_quota_gap(baseline.total_emission_t, baseline_summary)

    for r in results:
        if r.reduction_t >= baseline_gap.gap_t and baseline_gap.gap_t > 0:
            global_recommendations.append(
                f"「{r.name}」情景可完全覆盖配额缺口（缺口{baseline_gap.gap_t} tCO₂）"
            )

    return ScenarioComparison(
        baseline_emission=baseline.total_emission_t,
        scenarios=results,
        recommendations=global_recommendations,
    )


def find_optimal_reduction(
    baseline_fleet: List[VehicleGroupData],
    budget: Optional[float] = None,
) -> ScenarioComparison:
    """
    在预算约束下寻找最优减排组合

    策略：枚举所有可能的减排组合，选择性价比最高的方案。
    如果未指定预算，则选择减排量最大的方案。

    Args:
        baseline_fleet: 基线车队
        budget: 预算上限（元），None表示无预算限制

    Returns:
        ScenarioComparison: 最优方案对比结果
    """
    # 构建所有可能的减排措施
    base_measures = []

    # 为每种车型生成"替换为新能源"措施
    for group in baseline_fleet:
        if "新能源" not in group.vehicle_type and "LNG" not in group.vehicle_type:
            base_measures.append({
                "name": f"将{group.count}辆{group.vehicle_type}替换为新能源物流车",
                "count": group.count,
                "change_key": f"替换为新能源物流车",
            })

    # 为柴油车型生成"更换LNG"措施
    for group in baseline_fleet:
        if "柴油" in group.vehicle_type and group.count > 0:
            base_measures.append({
                "name": f"将{group.count}辆{group.vehicle_type}更换LNG",
                "count": group.count,
                "change_key": "重型货车更换LNG",
            })

    # 生成"提升满载率"措施（覆盖所有车辆）
    total_vehicles = sum(g.count for g in baseline_fleet)
    base_measures.append({
        "name": f"将所有{total_vehicles}辆车的满载率提升至0.8",
        "count": total_vehicles,
        "change_key": "提升满载率至0.8",
    })

    # 生成单措施情景
    scenarios = []
    for m in base_measures:
        scenarios.append(ReductionScenario(
            name=m["name"],
            description=f"单措施：{m['name']}",
            changes={m["change_key"]: m["count"]},
        ))

    # 生成双措施组合情景（两两组合）
    for i in range(len(base_measures)):
        for j in range(i + 1, len(base_measures)):
            mi, mj = base_measures[i], base_measures[j]
            if mi["change_key"] == mj["change_key"]:
                continue  # 跳过相同类型的措施组合
            combined_changes = {mi["change_key"]: mi["count"], mj["change_key"]: mj["count"]}
            scenarios.append(ReductionScenario(
                name=f"{mi['name']} + {mj['name']}",
                description=f"双措施组合：{mi['name']} & {mj['name']}",
                changes=combined_changes,
            ))

    # 三措施组合（仅当措施数≥3时）
    if len(base_measures) >= 3:
        for i in range(len(base_measures)):
            for j in range(i + 1, len(base_measures)):
                for k in range(j + 1, len(base_measures)):
                    m1, m2, m3 = base_measures[i], base_measures[j], base_measures[k]
                    if len({m1["change_key"], m2["change_key"], m3["change_key"]}) < 3:
                        continue
                    combined_changes = {
                        m1["change_key"]: m1["count"],
                        m2["change_key"]: m2["count"],
                        m3["change_key"]: m3["count"],
                    }
                    scenarios.append(ReductionScenario(
                        name=f"组合：{m1['name']} + {m2['name']} + {m3['name']}",
                        description=f"三措施组合",
                        changes=combined_changes,
                    ))

    # 计算所有情景并筛选
    comparison = compare_scenarios(baseline_fleet, scenarios)

    # 按性价比（元/tCO₂减排）排序
    scored = []
    for r in comparison.scenarios:
        savings = r.cost_savings.get("节省_元", 0)
        reduction = r.reduction_t
        cost_efficiency = savings / reduction if reduction > 0 else 0
        scored.append((r, cost_efficiency))

    scored.sort(key=lambda x: x[1], reverse=True)

    # 如果有预算，选择性价比最高且在预算内的方案
    if budget is not None and scored:
        best = scored[0][0]
        baseline_cost_val = best.cost_savings.get("基线合规成本_元", 0)
        # 简化：假设减排投资约为合规成本节省的30-50%
        estimated_investment = baseline_cost_val * 0.4 if baseline_cost_val > 0 else 0
        if estimated_investment <= budget or estimated_investment == 0:
            # 最优方案在预算内
            comparison.scenarios = sorted([best], key=lambda x: x.reduction_pct, reverse=True)
            comparison.scenarios[0].name = f"最优方案（{best.name}）"
        else:
            comparison.scenarios = sorted([best], key=lambda x: x.reduction_pct, reverse=True)
            comparison.scenarios[0].name = f"推荐方案（{best.name}，预算{budget}元）"
    else:
        # 无预算限制，选择减排量最大的
        if scored:
            best = scored[0][0]
            comparison.scenarios = sorted([best], key=lambda x: x.reduction_pct, reverse=True)
            comparison.scenarios[0].name = f"最优方案（{best.name}）"

    return comparison


# ============================================================
# 辅助函数
# ============================================================

def _generate_recommendations(
    baseline_fleet: List[VehicleGroupData],
    changes: dict,
    reduction_t: float,
    reduction_pct: float,
) -> list:
    """
    根据减排分析结果生成具体建议

    Args:
        baseline_fleet: 基线车队
        changes: 减排措施
        reduction_t: 减排量 (tCO₂)
        reduction_pct: 减排百分比

    Returns:
        建议列表
    """
    recommendations = []

    # 基础建议
    if reduction_t > 0:
        recommendations.append(
            f"✅ 该方案可减少 {reduction_t} tCO₂ 排放，减排比例 {reduction_pct}%"
        )

    # 按车型给出针对性建议
    fleet_summary = {}
    for g in baseline_fleet:
        fleet_summary[g.vehicle_type] = fleet_summary.get(g.vehicle_type, 0) + g.count

    # 如果有替换新能源的措施
    if any("新能源" in k for k in changes):
        ne_count = sum(count for k, count in changes.items() if "新能源" in k)
        recommendations.append(
            f"💡 替换 {ne_count} 辆燃油车为新能源车，可显著降低直接排放"
        )
        recommendations.append(
            "💡 建议关注新能源车全生命周期碳排放（电池生产、电力来源）"
        )

    # 如果有LNG替换措施
    if any("LNG" in k for k in changes):
        recommendations.append(
            "💡 LNG相比柴油可减少约15-18%的碳排放，适合作为过渡方案"
        )
        recommendations.append(
            "⚠️ LNG存在甲烷逃逸排放问题，需关注燃料链排放"
        )

    # 如果有满载率提升措施
    if any("满载率" in k for k in changes):
        recommendations.append(
            "💡 提升满载率是低成本减排方式，建议优化路线规划和装载调度"
        )
        recommendations.append(
            "💡 可考虑引入智能调度系统提升整体运营效率"
        )

    # 通用建议
    if reduction_pct < 10:
        recommendations.append(
            "⚠️ 当前减排力度较小（<10%），建议叠加多种减排措施"
        )
    elif reduction_pct >= 50:
        recommendations.append(
            "✅ 该方案减排力度较大（≥50%），可显著改善碳资产状况"
        )

    # 配额缺口相关建议
    baseline = calculate_emission(baseline_fleet)
    baseline_summary = {g.vehicle_type: g.count for g in baseline_fleet}
    baseline_gap = estimate_quota_gap(baseline.total_emission_t, baseline_summary)

    if baseline_gap.gap_t > 0:
        remaining_gap = baseline_gap.gap_t - reduction_t
        if remaining_gap > 0:
            recommendations.append(
                f"⚠️ 实施该方案后仍存在 {remaining_gap:.0f} tCO₂ 配额缺口，建议继续优化"
            )
        else:
            recommendations.append(
                "✅ 实施该方案后可完全覆盖配额缺口，无需额外购买配额"
            )

    return recommendations
