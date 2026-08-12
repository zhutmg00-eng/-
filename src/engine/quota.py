"""碳配额缺口估算

配额计算公式：
    Q = Σ (n_i × q_benchmark_i × adjustment_factor)
    Gap = E - Q

    若 Gap > 0 → 配额缺口，需购买
    若 Gap < 0 → 配额盈余，可出售
"""
from dataclasses import dataclass

# ============================================================
# 配额基准值（tCO₂/辆/年）
# 参照碳市场历史配额分配数据估算
# 实际值需跟踪最新配额分配方案更新
# ============================================================
QUOTA_BENCHMARK = {
    "重型柴油货车": 72.0,
    "中型柴油货车": 42.0,
    "轻型柴油货车": 22.0,
    "微型汽油货车": 12.0,
    "LNG重型货车": 58.0,
    "新能源物流车": 0.0,  # 电动车纳入配额管理方式待定
}

# 基准线法默认调整因子
ADJUSTMENT_FACTOR = 1.0


@dataclass
class QuotaGapResult:
    """配额缺口结果"""
    total_quota_t: float       # 免费配额总量 (tCO₂)
    total_emission_t: float    # 实际排放 (tCO₂)
    gap_t: float               # 缺口（正=需购买，负=盈余）
    gap_status: str            # "缺口" | "盈余" | "平衡"
    quota_by_type: dict        # 分车型配额明细


def estimate_quota_gap(emission_total: float, fleet_summary: dict) -> QuotaGapResult:
    """
    估算企业碳配额缺口

    Args:
        emission_total: 企业年度碳排放基线 (tCO₂)
        fleet_summary: 各车型车辆数 {"重型柴油货车": 50, "中型柴油货车": 30, ...}

    Returns:
        QuotaGapResult: 配额缺口结果
    """
    total_quota = 0.0
    quota_by_type = {}

    for vtype, count in fleet_summary.items():
        benchmark = QUOTA_BENCHMARK.get(vtype, 0)
        type_quota = count * benchmark * ADJUSTMENT_FACTOR
        total_quota += type_quota
        quota_by_type[vtype] = {
            "车辆数": count,
            "基准值_t_per_辆": benchmark,
            "配额_t": round(type_quota, 2),
        }

    gap = emission_total - total_quota

    if abs(gap) < emission_total * 0.01:  # 差距小于1%视为平衡
        status = "平衡"
    elif gap > 0:
        status = "缺口"
    else:
        status = "盈余"

    return QuotaGapResult(
        total_quota_t=round(total_quota, 2),
        total_emission_t=round(emission_total, 2),
        gap_t=round(gap, 2),
        gap_status=status,
        quota_by_type=quota_by_type,
    )
