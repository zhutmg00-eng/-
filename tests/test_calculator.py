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
from src.engine.quota import estimate_quota_gap, QUOTA_BENCHMARK
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
# 配额缺口测试
# ============================================================

class TestQuotaGap:
    def test_gap_positive(self):
        """排放>配额 → 缺口"""
        fleet_summary = {"重型柴油货车": 50}
        result = estimate_quota_gap(4000.0, fleet_summary)
        # 配额 = 50 × 72 = 3600
        assert result.gap_t == 400.0
        assert result.gap_status == "缺口"

    def test_gap_negative(self):
        """排放<配额 → 盈余"""
        fleet_summary = {"重型柴油货车": 50}
        result = estimate_quota_gap(3000.0, fleet_summary)
        assert result.gap_t == -600.0
        assert result.gap_status == "盈余"

    def test_gap_balanced(self):
        """排放≈配额 → 平衡"""
        fleet_summary = {"重型柴油货车": 50}
        result = estimate_quota_gap(3600.0, fleet_summary)
        assert result.gap_status == "平衡"

    def test_ev_no_quota(self):
        """新能源物流车配额基准为0"""
        assert QUOTA_BENCHMARK["新能源物流车"] == 0.0


# ============================================================
# 碳价成本测试
# ============================================================

class TestCarbonPrice:
    def test_positive_gap_with_mock_price(self):
        """有缺口时返回成本估算"""
        result = estimate_compliance_cost(1000.0, None)
        assert result["合规需求"] == "需购买配额"
        assert result["配额缺口_t"] == 1000.0
        assert result["预估合规成本_参考价"] > 0

    def test_negative_gap(self):
        """盈余时返回收益估算"""
        result = estimate_compliance_cost(-500.0, None)
        assert result["合规需求"] == "配额盈余"
        assert result["预估收益_low"] > 0

    def test_zero_gap(self):
        """零缺口时也返回盈余"""
        result = estimate_compliance_cost(0.0, None)
        assert "盈余" in result["合规需求"]
