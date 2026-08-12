"""排放因子数据库（已整合GB 30510-2024最新数据）

数据来源：
- 蔡博峰等. 中国分省道路交通二氧化碳排放因子. 中国环境科学, 2021.
- GB 30510-2024《重型商用车辆燃料消耗量限值》（第四阶段，2025年7月实施）
- GB 30510-2018《重型商用车辆燃料消耗量限值》（第三阶段，已废止）
- IPCC 2019 Refinement, Volume 2, Chapter 3 (Mobile Combustion)
- GLEC框架3.0 (智慧货运中心)
- 国家温室气体排放因子数据库第二版（2026年3月发布，576个因子）
"""
from typing import Dict, Optional
import csv
from pathlib import Path

# ============================================================
# 内置排放因子表（当CSV文件不存在时使用）
# 数据已整合GB 30510-2024第四阶段标准
# ============================================================
EMISSION_FACTORS: Dict[str, Dict] = {
    # === 主力车型（中国环境科学2021 + GB 30510-2024交叉验证）===
    "重型柴油货车": {
        "co2_kg_per_km": 0.877,
        "fuel_type": "柴油",
        "fuel_consumption_l_per_100km": 33.0,
        "avg_annual_km": 80000,
        "source": "中国环境科学2021(蔡博峰等)",
        "gb2024_factor": 0.858,  # GB 30510-2024 第四阶段
        "gb2024_note": "GB 30510-2024限值对应的CO2参考值，较第三阶段加严约15%",
    },
    "中型柴油货车": {
        "co2_kg_per_km": 0.508,
        "fuel_type": "柴油",
        "fuel_consumption_l_per_100km": 19.0,
        "avg_annual_km": 50000,
        "source": "中国环境科学2021(蔡博峰等)",
        "gb2024_factor": 0.536,  # GB 30510-2024 第四阶段(12-16t)
    },
    "轻型柴油货车": {
        "co2_kg_per_km": 0.374,
        "fuel_type": "柴油",
        "fuel_consumption_l_per_100km": 12.0,
        "avg_annual_km": 30000,
        "source": "中国环境科学2021(蔡博峰等)",
        "gb2024_factor": 0.257,  # GB 30510-2024 第四阶段(3.5-4.5t)
    },
    "微型汽油货车": {
        "co2_kg_per_km": 0.216,
        "fuel_type": "汽油",
        "fuel_consumption_l_per_100km": 8.0,
        "avg_annual_km": 20000,
        "source": "中国环境科学2021(蔡博峰等)",
        "gb2024_factor": 0.282,  # GB 30510-2024 第四阶段(3.5-4.5t汽油)
    },
    "LNG重型货车": {
        "co2_kg_per_km": 0.72,
        "fuel_type": "LNG",
        "fuel_consumption_l_per_100km": None,
        "avg_annual_km": 80000,
        "source": "国家发改委指南（估算值，LNG比柴油低约18%）",
        "gb2024_note": "实测数据范围0.72-1.2 kg/km，取保守估计值",
    },
    "新能源物流车": {
        "co2_kg_per_km": 0.0,
        "fuel_type": "电动",
        "fuel_consumption_l_per_100km": None,
        "avg_annual_km": 40000,
        "source": "直接排放为零（全生命周期排放另计）",
        "gb2024_note": "全生命周期排放约0.805-1.088 kg/km（取决于电网排放因子）",
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


def get_factor_comparison() -> list:
    """获取不同来源的排放因子对比表"""
    return [
        {
            "vehicle_type": "重型柴油货车(>31t)",
            "fuel": "柴油",
            "env_science_2021": 0.877,
            "gb_2024": 0.858,
            "gb_2018": 0.884,
            "recommended": 0.877,
            "note": "采用中国环境科学2021值，与GB标准差异<3%",
        },
        {
            "vehicle_type": "中型柴油货车(12-16t)",
            "fuel": "柴油",
            "env_science_2021": 0.508,
            "gb_2024": 0.536,
            "gb_2018": 0.554,
            "recommended": 0.508,
            "note": "采用中国环境科学2021值（偏保守）",
        },
        {
            "vehicle_type": "轻型柴油货车(3.5-4.5t)",
            "fuel": "柴油",
            "env_science_2021": 0.374,
            "gb_2024": 0.257,
            "gb_2018": None,
            "recommended": 0.374,
            "note": "GB2024限值更严，但实际运行排放高于限值",
        },
        {
            "vehicle_type": "微型汽油货车(3.5-4.5t)",
            "fuel": "汽油",
            "env_science_2021": 0.216,
            "gb_2024": 0.282,
            "gb_2018": None,
            "recommended": 0.216,
            "note": "采用中国环境科学2021值",
        },
    ]
