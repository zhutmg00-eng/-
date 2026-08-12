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
        assert "缺口" in result["quota_gap"]["状态"] or "盈余" in result["quota_gap"]["状态"]

    def test_calculate_empty_fleet(self):
        """空车队"""
        response = client.post("/api/calculate", json={
            "company_name": "空公司",
            "fleet": []
        })
        assert response.status_code == 200
        result = response.json()
        assert result["total_emission_t"] == 0
        assert result["total_vehicles"] == 0

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
