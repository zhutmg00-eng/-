"""碳排放计算引擎单元测试"""
import pytest
import sys
from pathlib import Path

# 确保src在路径中
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.engine.calculator import (
    VehicleGroupData,
    calculate_emission,
    calculate_load_adjustment,
)
from src.engine.emission_factors import get_emission_factor, list_vehicle_types
from src.engine.quota import (
    SIMULATION_BUDGET_BENCHMARK,
    build_simulation_budget_benchmarks,
    estimate_quota_gap,
)
from src.engine.carbon_price import estimate_compliance_cost


# ============================================================
# 排放因子测试
# ============================================================

class TestEmissionFactors:
    def test_get_heavy_truck_factor(self):
        ef = get_emission_factor("重型柴油货车")
        assert ef is not None
        assert ef["co2_kg_per_km"] == 0.877
        assert ef["fuel_type"] == "柴油"

    def test_get_ev_factor(self):
        ef = get_emission_factor("新能源物流车")
        assert ef is not None
        assert ef["co2_kg_per_km"] == 0.0

    def test_get_unknown_type(self):
        ef = get_emission_factor("不存在的车型")
        assert ef is None

    def test_list_vehicle_types(self):
        types = list_vehicle_types()
        assert len(types) >= 6
        assert "重型柴油货车" in types
        assert "新能源物流车" in types

    def test_reference_only_electric_factors_are_not_operational_types(self):
        types = list_vehicle_types()
        assert "纯电动重卡(全生命周期)" not in types
        assert "纯电动重卡(河北电网)" not in types
        assert get_emission_factor("纯电动重卡(全生命周期)") is None


# ============================================================
# 碳排放计算测试
# ============================================================

class TestCalculator:
    def test_heavy_diesel_truck(self):
        """50辆重型柴油货车 → 预期约3508 tCO₂"""
        fleet = [
            VehicleGroupData(
                vehicle_type="重型柴油货车",
                count=50,
                annual_km=80000,
                load_factor=0.75,
            )
        ]
        result = calculate_emission(fleet)
        expected = 50 * 80000 * 0.877 / 1000  # 3508.0
        assert abs(result.total_emission_t - expected) < 10
        assert result.total_vehicles == 50

    def test_empty_fleet(self):
        """空车队返回零排放"""
        result = calculate_emission([])
        assert result.total_emission_t == 0
        assert result.total_vehicles == 0

    def test_mixed_fleet(self):
        """混合车队排放为各车型之和"""
        fleet = [
            VehicleGroupData("重型柴油货车", 20, 80000, 0.75),
            VehicleGroupData("中型柴油货车", 30, 50000, 0.75),
            VehicleGroupData("新能源物流车", 10, 40000, 0.75),
        ]
        result = calculate_emission(fleet)
        # 新能源车直接排放为0
        expected = (20 * 80000 * 0.877 + 30 * 50000 * 0.508) / 1000
        assert abs(result.total_emission_t - expected) < 10
        assert result.total_vehicles == 60

    def test_ev_zero_emission(self):
        """新能源物流车直接排放为零"""
        fleet = [VehicleGroupData("新能源物流车", 100, 40000, 0.75)]
        result = calculate_emission(fleet)
        assert result.total_emission_t == 0.0

    def test_load_factor_adjustment(self):
        """满载率低于75%时排放应增加"""
        fleet_full = [VehicleGroupData("重型柴油货车", 10, 80000, 0.75)]
        fleet_low = [VehicleGroupData("重型柴油货车", 10, 80000, 0.50)]
        result_full = calculate_emission(fleet_full)
        result_low = calculate_emission(fleet_low)
        assert result_low.total_emission_t > result_full.total_emission_t

    def test_load_adjustment_at_threshold(self):
        """满载率=75%时调整系数=1.0"""
        assert calculate_load_adjustment(0.75) == 1.0
        assert calculate_load_adjustment(0.80) == 1.0
        assert calculate_load_adjustment(1.0) == 1.0

    def test_load_adjustment_below_threshold(self):
        """满载率<75%时调整系数>1.0"""
        assert calculate_load_adjustment(0.50) > 1.0
        assert calculate_load_adjustment(0.0) > calculate_load_adjustment(0.50)

    def test_unsupported_vehicle_type(self):
        """不支持的车型应抛出ValueError"""
        fleet = [VehicleGroupData("不存在的车型", 1, 1000, 0.75)]
        with pytest.raises(ValueError, match="不支持的车型"):
            calculate_emission(fleet)

    def test_emission_by_type_percentages(self):
        """各车型排放占比之和应≈100%"""
        fleet = [
            VehicleGroupData("重型柴油货车", 20, 80000, 0.75),
            VehicleGroupData("中型柴油货车", 30, 50000, 0.75),
        ]
        result = calculate_emission(fleet)
        total_pct = sum(v["占比"] for v in result.emission_by_type.values())
        assert abs(total_pct - 100.0) < 0.5


# ============================================================
# 模拟碳预算差额测试
# ============================================================

class TestQuotaGap:
    def test_gap_positive(self):
        """排放高于模拟预算。"""
        fleet_summary = {"重型柴油货车": 50}
        result = estimate_quota_gap(4000.0, fleet_summary)
        # 模拟预算 = 50 × 63.144 = 3157.2
        assert result.gap_t == 842.8
        assert result.gap_status == "超出预算"

    def test_gap_negative(self):
        """排放低于模拟预算。"""
        fleet_summary = {"重型柴油货车": 50}
        result = estimate_quota_gap(3000.0, fleet_summary)
        assert result.gap_t == -157.2
        assert result.gap_status == "低于预算"

    def test_gap_balanced(self):
        """排放约等于模拟预算。"""
        fleet_summary = {"重型柴油货车": 50}
        result = estimate_quota_gap(3157.2, fleet_summary)
        assert result.gap_status == "基本平衡"

    def test_ev_no_quota(self):
        """新能源物流车直接运营模拟预算基准为0。"""
        assert SIMULATION_BUDGET_BENCHMARK["新能源物流车"] == 0.0

    def test_budget_benchmark_matches_documented_formula(self):
        expected = 0.877 * 80000 / 1000 * 0.90
        assert SIMULATION_BUDGET_BENCHMARK["重型柴油货车"] == pytest.approx(expected)

    def test_budget_covers_every_supported_operational_vehicle(self):
        assert set(list_vehicle_types()) == set(SIMULATION_BUDGET_BENCHMARK)

    def test_budget_target_is_configurable(self):
        no_reduction = build_simulation_budget_benchmarks(0)
        assert no_reduction["重型柴油货车"] == 70.16
        result = estimate_quota_gap(3508.0, {"重型柴油货车": 50}, reduction_target=0)
        assert result.gap_status == "基本平衡"

    @pytest.mark.parametrize("target", [-0.01, 1.0])
    def test_budget_target_rejects_invalid_values(self, target):
        with pytest.raises(ValueError, match="情景减排目标"):
            build_simulation_budget_benchmarks(target)


# ============================================================
# 碳价成本测试
# ============================================================

class TestCarbonPrice:
    def test_positive_gap_with_mock_price(self):
        """超出模拟预算时返回情景金额。"""
        result = estimate_compliance_cost(1000.0, None)
        assert result["情景判断"] == "超出模拟碳预算"
        assert result["预算差额_t"] == 1000.0
        assert result["情景成本_参考价"] > 0
        assert "不代表" in result["备注"]

    def test_negative_gap(self):
        """低于模拟预算时返回潜在价值情景。"""
        result = estimate_compliance_cost(-500.0, None)
        assert result["情景判断"] == "低于模拟碳预算"
        assert result["潜在价值_low"] > 0
        assert "不代表" in result["备注"]

    def test_zero_gap(self):
        """零差额时返回基本平衡。"""
        result = estimate_compliance_cost(0.0, None)
        assert result["情景判断"] == "基本平衡"
        assert result["预算结余_t"] == 0
