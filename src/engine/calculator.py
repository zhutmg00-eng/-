"""碳排放基线计算引擎

核心公式：
    E = Σ (n_i × d_i × EF_i × LF_i) / 1000

    其中:
      E    = 企业年度直接运营排放总量 (tCO2e/年)
      n_i  = 第i类车型车辆数量 (辆)
      d_i  = 第i类车型年均运营里程 (km/年)
      EF_i = 第i类车型CO₂排放因子 (kgCO₂/km)
      LF_i = 满载率调整系数: LF_i = 1 + α×(0.75 - l_i)  当 l_i < 0.75
"""
from dataclasses import dataclass
from typing import List
from src.engine.emission_factors import get_emission_factor
from src.config import LOAD_FACTOR_ALPHA, LOAD_FACTOR_THRESHOLD


@dataclass
class VehicleGroupData:
    """车队子集（内部计算用）"""
    vehicle_type: str
    count: int
    annual_km: float
    load_factor: float = 0.75


@dataclass
class CarbonBaselineResult:
    """碳排放基线计算结果"""
    total_emission_t: float
    emission_by_type: dict
    total_vehicles: int


def calculate_load_adjustment(load_factor: float) -> float:
    """
    计算满载率调整系数

    当满载率低于75%时，单位排放上升（货物分摊效率下降）
    当满载率≥75%时，不做调整
    """
    if load_factor < LOAD_FACTOR_THRESHOLD:
        return 1 + LOAD_FACTOR_ALPHA * (LOAD_FACTOR_THRESHOLD - load_factor)
    return 1.0


def calculate_emission(fleet: List[VehicleGroupData]) -> CarbonBaselineResult:
    """
    计算企业年度碳排放基线

    Args:
        fleet: 企业车队分组列表

    Returns:
        CarbonBaselineResult: 碳排放基线结果

    Raises:
        ValueError: 当包含不支持的车型时
    """
    total_emission = 0.0
    emission_by_type = {}
    total_vehicles = 0

    for group in fleet:
        ef = get_emission_factor(group.vehicle_type)
        if ef is None:
            raise ValueError(f"不支持的车型: {group.vehicle_type}")

        # 满载率调整系数
        load_adjustment = calculate_load_adjustment(group.load_factor)

        # 分类排放量 = 车辆数 × 年均里程 × 排放因子(kg/km) × 满载率调整 / 1000 → 吨
        group_emission = (
            group.count
            * group.annual_km
            * ef["co2_kg_per_km"]
            * load_adjustment
            / 1000
        )

        if group.vehicle_type in emission_by_type:
            prev = emission_by_type[group.vehicle_type]
            new_emission = prev["排放量_tCO2"] + round(group_emission, 2)
            new_count = prev["车辆数"] + group.count
            emission_by_type[group.vehicle_type] = {
                "排放量_tCO2": round(new_emission, 2),
                "占比": 0.0,
                "车辆数": new_count,
                "单辆排放_tCO2": round(new_emission / new_count, 2) if new_count else 0,
                "排放因子_kg_per_km": ef["co2_kg_per_km"],
                "满载率调整系数": round(load_adjustment, 4),
                "燃料类型": ef["fuel_type"],
            }
        else:
            emission_by_type[group.vehicle_type] = {
                "排放量_tCO2": round(group_emission, 2),
                "占比": 0.0,  # 稍后计算
                "车辆数": group.count,
                "单辆排放_tCO2": round(group_emission / group.count, 2) if group.count else 0,
                "排放因子_kg_per_km": ef["co2_kg_per_km"],
                "满载率调整系数": round(load_adjustment, 4),
                "燃料类型": ef["fuel_type"],
            }

        total_emission += group_emission
        total_vehicles += group.count

    # 计算各车型排放占比
    if total_emission > 0:
        for vtype in emission_by_type:
            emission_by_type[vtype]["占比"] = round(
                emission_by_type[vtype]["排放量_tCO2"] / total_emission * 100, 1
            )

    return CarbonBaselineResult(
        total_emission_t=round(total_emission, 2),
        emission_by_type=emission_by_type,
        total_vehicles=total_vehicles,
    )
