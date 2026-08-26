"""API接口测试"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


class TestAPI:
    def test_health_check(self):
        """健康检查"""
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_vehicle_types(self):
        """车型列表"""
        response = client.get("/api/vehicle-types")
        assert response.status_code == 200
        data = response.json()
        assert "vehicle_types" in data
        assert len(data["vehicle_types"]) >= 6

    def test_calculate_heavy_trucks(self):
        """计算重型货车碳排放"""
        response = client.post("/api/calculate", json={
            "company_name": "测试物流公司",
            "fleet": [{
                "vehicle_type": "重型柴油货车",
                "count": 50,
                "annual_km": 80000,
                "load_factor": 0.75,
            }]
        })
        assert response.status_code == 200
        result = response.json()
        assert result["company_name"] == "测试物流公司"
        assert result["total_emission_t"] > 3000
        assert result["total_vehicles"] == 50
        assert result["carbon_budget"]["状态"] in {"超出预算", "低于预算", "基本平衡"}
        assert result["carbon_budget"]["模拟碳预算_t"] == 3600.0
        assert "购电间接排放" in result["methodology_note"]

    def test_calculate_empty_fleet(self):
        """空车队应在进入计算引擎前被拒绝"""
        response = client.post("/api/calculate", json={
            "company_name": "空公司",
            "fleet": []
        })
        assert response.status_code == 422

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("count", -1),
            ("annual_km", -100),
            ("load_factor", 1.2),
            ("load_factor", -0.1),
        ],
    )
    def test_calculate_rejects_invalid_vehicle_values(self, field, value):
        vehicle = {
            "vehicle_type": "重型柴油货车",
            "count": 1,
            "annual_km": 10000,
            "load_factor": 0.75,
        }
        vehicle[field] = value
        response = client.post(
            "/api/calculate",
            json={"company_name": "边界测试", "fleet": [vehicle]},
        )
        assert response.status_code == 422

    def test_calculate_rejects_unknown_vehicle_type(self):
        response = client.post("/api/calculate", json={
            "company_name": "未知车型测试",
            "fleet": [{
                "vehicle_type": "不存在的车型",
                "count": 1,
                "annual_km": 10000,
                "load_factor": 0.75,
            }],
        })
        assert response.status_code == 422

    def test_calculate_rejects_blank_company_name(self):
        response = client.post("/api/calculate", json={
            "company_name": "   ",
            "fleet": [{
                "vehicle_type": "重型柴油货车",
                "count": 1,
                "annual_km": 10000,
                "load_factor": 0.75,
            }],
        })
        assert response.status_code == 422

    def test_calculate_mixed_fleet(self):
        """混合车队"""
        response = client.post("/api/calculate", json={
            "company_name": "混合车队公司",
            "fleet": [
                {"vehicle_type": "重型柴油货车", "count": 20, "annual_km": 80000, "load_factor": 0.75},
                {"vehicle_type": "中型柴油货车", "count": 30, "annual_km": 50000, "load_factor": 0.75},
                {"vehicle_type": "新能源物流车", "count": 10, "annual_km": 40000, "load_factor": 0.75},
            ]
        })
        assert response.status_code == 200
        result = response.json()
        assert result["total_vehicles"] == 60
        # 新能源车排放为0，不影响总量
        assert result["total_emission_t"] > 0
