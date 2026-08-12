"""碳排放计算引擎统一入口"""
from src.engine.emission_factors import (
    get_emission_factor,
    list_vehicle_types,
    get_all_factors,
)
from src.engine.calculator import (
    VehicleGroupData,
    CarbonBaselineResult,
    calculate_emission,
    calculate_load_adjustment,
)
from src.engine.quota import (
    estimate_quota_gap,
    QuotaGapResult,
    QUOTA_BENCHMARK,
)
from src.engine.carbon_price import (
    estimate_compliance_cost,
    load_carbon_price_data,
    calculate_price_stats,
)

__all__ = [
    "get_emission_factor",
    "list_vehicle_types",
    "get_all_factors",
    "VehicleGroupData",
    "CarbonBaselineResult",
    "calculate_emission",
    "calculate_load_adjustment",
    "estimate_quota_gap",
    "QuotaGapResult",
    "QUOTA_BENCHMARK",
    "estimate_compliance_cost",
    "load_carbon_price_data",
    "calculate_price_stats",
]
