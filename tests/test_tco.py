"""TCO (Total Cost of Ownership) 引擎与投资决策单元测试。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.engine.calculator import VehicleGroupData
from src.engine.reduction import analyze_reduction_scenario
from src.engine.tco import (
    DEFAULT_TCO_BENCHMARKS,
    TCOEconomicParameters,
    VehicleTCOBenchmark,
    calculate_fleet_tco,
    calculate_single_vehicle_tco,
    get_tco_benchmark,
)

client = TestClient(app)


class TestTCOBasics:
    def test_benchmark_coverage(self):
        """验证主流货车类型均具备默认 TCO 基准参数。"""
        assert "重型柴油货车" in DEFAULT_TCO_BENCHMARKS
        assert "中型柴油货车" in DEFAULT_TCO_BENCHMARKS
        assert "轻型柴油货车" in DEFAULT_TCO_BENCHMARKS
        assert "微型汽油货车" in DEFAULT_TCO_BENCHMARKS

    def test_heavy_truck_tco_math(self):
        """验证 10 辆重型柴油货车替换为纯电重卡的核心数学计算。"""
        res = calculate_single_vehicle_tco(
            vehicle_type="重型柴油货车",
            replace_count=10,
            annual_km=80000.0,
            annual_co2_reduction_t=701.6,
        )
        # 1. CAPEX: (65 - 35 + 3)万 × 10 = 330 万元 = 3,300,000 元
        assert res.delta_capex_total_yuan == 3300000.0
        assert res.delta_capex_per_vehicle_yuan == 330000.0

        # 2. 单车油费: 800 × 33 × 7.5 = 198,000 元
        assert res.annual_fuel_cost_per_vehicle_yuan == 198000.0

        # 3. 单车电费: 800 × 140 × 0.8 = 89,600 元
        assert res.annual_elec_cost_per_vehicle_yuan == 89600.0

        # 4. 单车能耗年节省: 198,000 - 89,600 = 108,400 元
        # 10辆车总能耗年节省: 1,084,000 元
        assert res.annual_energy_saving_total_yuan == 1084000.0

        # 5. 10辆车维保年节省: 15,000 × 0.35 × 10 = 52,500 元
        assert res.annual_maintenance_saving_total_yuan == 52500.0

        # 6. 总运营节省 ΔOPEX: 1,084,000 + 52,500 = 1,136,500 元/年
        assert res.annual_opex_saving_total_yuan == 1136500.0

        # 7. 静态投资回收期: 3,300,000 / 1,136,500 ≈ 2.90 年
        assert res.payback_period_years is not None
        assert round(res.payback_period_years, 2) == 2.90

        # 8. MAC 为负数（代表全周期净收益）
        assert res.mac_yuan_per_tco2e is not None
        assert res.mac_yuan_per_tco2e < 0

        # 9. 现金流序列验证: 第0年为 -330万，第5年为正收益
        assert res.yearly_cumulative_cashflow_yuan[0] == -3300000.0
        assert res.yearly_cumulative_cashflow_yuan[5] > 0

    def test_light_truck_tco_math(self):
        """验证轻型柴油货车替换为纯电轻卡计算。"""
        res = calculate_single_vehicle_tco(
            vehicle_type="轻型柴油货车",
            replace_count=5,
            annual_km=30000.0,
            annual_co2_reduction_t=56.1,
        )
        # CAPEX: (17 - 11 + 0.8)万 × 5 = 34 万元
        assert res.delta_capex_total_yuan == 340000.0
        assert res.payback_period_years is not None
        assert res.payback_period_years > 0


class TestTCOFleetAndCustom:
    def test_fleet_tco_combination(self):
        """测试车队多车型替换组合 TCO 计算。"""
        replacements = [
            {
                "vehicle_type": "重型柴油货车",
                "replace_count": 5,
                "annual_km": 80000.0,
                "annual_co2_reduction_t": 350.8,
            },
            {
                "vehicle_type": "轻型柴油货车",
                "replace_count": 10,
                "annual_km": 30000.0,
                "annual_co2_reduction_t": 112.2,
            },
        ]
        fleet_res = calculate_fleet_tco(replacements)
        assert fleet_res.total_replace_count == 15
        assert fleet_res.total_delta_capex_yuan > 0
        assert fleet_res.total_annual_opex_saving_yuan > 0
        assert fleet_res.overall_payback_period_years is not None
        assert len(fleet_res.yearly_cashflow) == 6

        dict_output = fleet_res.to_dict()
        assert "total_delta_capex_wan" in dict_output
        assert "overall_mac_yuan_per_tco2e" in dict_output

    def test_custom_economic_parameters(self):
        """测试高油价与低电价情景下的回收期缩短。"""
        base_res = calculate_single_vehicle_tco(
            "重型柴油货车", 10, 80000.0, 701.6
        )
        favorable_params = TCOEconomicParameters(
            diesel_price_yuan_per_l=9.0,
            electricity_price_yuan_per_kwh=0.5,
        )
        favorable_res = calculate_single_vehicle_tco(
            "重型柴油货车", 10, 80000.0, 701.6, econ_params=favorable_params
        )
        assert favorable_res.annual_opex_saving_total_yuan > base_res.annual_opex_saving_total_yuan
        assert favorable_res.payback_period_years < base_res.payback_period_years


class TestTCOEdgeCases:
    def test_zero_replace_count(self):
        """替换数量为0时安全返回0值和None。"""
        res = calculate_single_vehicle_tco("重型柴油货车", 0, 80000.0, 0.0)
        assert res.delta_capex_total_yuan == 0.0
        assert res.payback_period_years is None
        assert res.mac_yuan_per_tco2e is None

    def test_unsupported_vehicle_type(self):
        """未知车型优雅降级。"""
        res = calculate_single_vehicle_tco("未知飞机", 5, 80000.0, 100.0)
        assert res.delta_capex_total_yuan == 0.0
        assert res.payback_period_years is None


class TestTCOAPI:
    def test_get_tco_defaults(self):
        """测试获取默认 TCO 参数接口。"""
        response = client.get("/api/tco/defaults")
        assert response.status_code == 200
        data = response.json()
        assert "benchmarks" in data
        assert "economic_parameters" in data
        assert "重型柴油货车" in data["benchmarks"]

    def test_post_tco_calculate(self):
        """测试 TCO 独立测算接口。"""
        payload = {
            "vehicle_type": "重型柴油货车",
            "replace_count": 10,
            "annual_km": 80000.0,
            "annual_co2_reduction_t": 701.6,
        }
        response = client.post("/api/tco/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["delta_capex_total_yuan"] == 3300000.0
        assert data["payback_period_years"] is not None
        assert data["mac_yuan_per_tco2e"] is not None

    def test_post_tco_calculate_invalid_type(self):
        """测试非法车型返回422。"""
        payload = {
            "vehicle_type": "宇宙飞船",
            "replace_count": 10,
            "annual_km": 80000.0,
        }
        response = client.post("/api/tco/calculate", json=payload)
        assert response.status_code == 422


class TestTCOReductionIntegration:
    def test_reduction_scenario_populates_tco(self):
        """测试减排情景分析中自动集成 TCO 计算与建议。"""
        fleet = [
            VehicleGroupData("重型柴油货车", 50, 80000, 0.75),
        ]
        scenario = analyze_reduction_scenario(
            baseline_fleet=fleet,
            changes={"替换为新能源物流车": 10},
        )
        assert scenario.tco_analysis is not None
        assert scenario.tco_analysis["total_replace_count"] == 10
        assert scenario.tco_analysis["overall_payback_period_years"] is not None

        # 验证生成的建议中包含 TCO 回收期信息
        tco_rec = [r for r in scenario.recommendations if "TCO 投资评估" in r]
        assert len(tco_rec) >= 1
        assert "静态投资回收期" in tco_rec[0]
