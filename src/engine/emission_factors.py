"""排放因子数据库

数据来源：
- 蔡博峰等. 中国分省道路交通二氧化碳排放因子. 中国环境科学, 2021.
- IPCC 2019 Refinement, Volume 2, Chapter 3 (Mobile Combustion)
- GB 30510-2018《重型商用车辆燃料消耗量限值》
- GLEC框架3.0 (智慧货运中心)
"""
from typing import Dict, Optional
import csv
from pathlib import Path

# ============================================================
# 内置排放因子表（当CSV文件不存在时使用）
# ============================================================
EMISSION_FACTORS: Dict[str, Dict] = {
    "重型柴油货车": {
        "co2_kg_per_km": 0.877,
        "fuel_type": "柴油",
        "fuel_consumption_l_per_100km": 33.0,
        "avg_annual_km": 80000,
        "source": "中国环境科学2021",
    },
    "中型柴油货车": {
        "co2_kg_per_km": 0.508,
        "fuel_type": "柴油",
        "fuel_consumption_l_per_100km": 19.0,
        "avg_annual_km": 50000,
        "source": "中国环境科学2021",
    },
    "轻型柴油货车": {
        "co2_kg_per_km": 0.374,
        "fuel_type": "柴油",
        "fuel_consumption_l_per_100km": 12.0,
        "avg_annual_km": 30000,
        "source": "中国环境科学2021",
    },
    "微型汽油货车": {
        "co2_kg_per_km": 0.216,
        "fuel_type": "汽油",
        "fuel_consumption_l_per_100km": 8.0,
        "avg_annual_km": 20000,
        "source": "中国环境科学2021",
    },
    "LNG重型货车": {
        "co2_kg_per_km": 0.72,
        "fuel_type": "LNG",
        "fuel_consumption_l_per_100km": None,
        "avg_annual_km": 80000,
        "source": "国家发改委指南（估算值，LNG比柴油低约18%）",
    },
    "新能源物流车": {
        "co2_kg_per_km": 0.0,
        "fuel_type": "电动",
        "fuel_consumption_l_per_100km": None,
        "avg_annual_km": 40000,
        "source": "直接排放为零（全生命周期排放另计）",
    },
}

# CSV文件路径
CSV_PATH = Path(__file__).parent.parent.parent / "data" / "raw" / "emission_factors.csv"


def load_from_csv() -> Dict[str, Dict]:
    """从CSV文件加载排放因子（如果存在）"""
    if not CSV_PATH.exists():
        return EMISSION_FACTORS

    factors = {}
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            vtype = row.get("车辆类型", "").strip()
            if not vtype:
                continue
            factors[vtype] = {
                "co2_kg_per_km": float(row.get("CO2排放因子(kg/km)", 0)),
                "fuel_type": row.get("燃料类型", ""),
                "fuel_consumption_l_per_100km": float(row["油耗(L/100km)"]) if row.get("油耗(L/100km)") else None,
                "avg_annual_km": int(row.get("年均里程参考(km)", 0)) or None,
                "source": row.get("数据来源", ""),
            }
    return factors if factors else EMISSION_FACTORS


def get_emission_factor(vehicle_type: str) -> Optional[Dict]:
    """获取指定车型的排放因子"""
    return EMISSION_FACTORS.get(vehicle_type)


def list_vehicle_types() -> list:
    """列出所有支持的车型"""
    return list(EMISSION_FACTORS.keys())


def get_all_factors() -> Dict[str, Dict]:
    """获取全部排放因子"""
    return EMISSION_FACTORS
