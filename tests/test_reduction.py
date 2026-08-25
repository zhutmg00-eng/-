"""减排分析引擎测试"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.engine.calculator import VehicleGroupData, calculate_emission
from src.engine.reduction import (
    ReductionScenario,
    ReductionAnalysis,
    _build_scenario_fleet,
    analyze_reduction_scenario,
    compare_scenarios,
    find_optimal_reduction,
)


class TestReductionEngine:
    @pytest.fixture
    def sample_fleet(self):
        return [
            VehicleGroupData(vehicle_type="重型柴油货车", count=50, annual_km=80000, load_factor=0.70),
            VehicleGroupData(vehicle_type="中型柴油货车", count=30, annual_km=50000, load_factor=0.75),
        ]

    def test_build_scenario_fleet_vehicle_count_preserved(self, sample_fleet):
        """情景车队总车辆数应与基线完全一致"""
        changes = {"替换为新能源物流车": 15}
        scenario_fleet = _build_scenario_fleet(sample_fleet, changes)
        total_scenario_vehicles = sum(g.count for g in scenario_fleet)
        total_base_vehicles = sum(g.count for g in sample_fleet)
        assert total_scenario_vehicles == total_base_vehicles == 80

        # 检查新能源车数量
        ev_count = sum(g.count for g in scenario_fleet if g.vehicle_type == "新能源物流车")
        assert ev_count == 15

    def test_analyze_reduction_scenario_positive_reduction(self, sample_fleet):
        """新能源替代应产生正向减排量与减排比例"""
        changes = {"替换为新能源物流车": 20}
        analysis = analyze_reduction_scenario(sample_fleet, changes)
        assert analysis.reduction_t > 0
        assert analysis.reduction_pct > 0
        assert analysis.scenario_emission < analysis.baseline_emission
        assert len(analysis.recommendations) > 0

    def test_analyze_reduction_load_factor_improvement(self, sample_fleet):
        """提升满载率应降低单位排放"""
        changes = {"提升满载率至85%": 50}
        analysis = analyze_reduction_scenario(sample_fleet, changes)
        assert analysis.reduction_t > 0
        assert analysis.scenario_emission < analysis.baseline_emission

    def test_compare_scenarios(self, sample_fleet):
        """多情景对比应按减排效果排序"""
        scenarios = [
            ReductionScenario(name="微量替代", description="替换5辆新能源", changes={"替换为新能源物流车": 5}),
            ReductionScenario(name="大量替代", description="替换30辆新能源", changes={"替换为新能源物流车": 30}),
        ]
        comparison = compare_scenarios(sample_fleet, scenarios)
        assert len(comparison.scenarios) == 2
        assert comparison.scenarios[0].reduction_t >= comparison.scenarios[1].reduction_t
        assert len(comparison.recommendations) > 0

    def test_find_optimal_reduction(self, sample_fleet):
        """最优减排求解应返回有效的推荐方案"""
        result = find_optimal_reduction(sample_fleet)
        assert len(result.scenarios) > 0
        assert result.scenarios[0].reduction_t > 0
