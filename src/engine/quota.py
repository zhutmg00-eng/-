"""物流企业模拟碳预算差额估算。

预算计算公式：
    Q = Σ (n_i × q_benchmark_i × adjustment_factor)
    Gap = E - Q

Q 仅用于科研原型的减排情景对标，不是法定碳配额。物流运输行业目前
未纳入全国碳市场配额管理，因此差额不代表履约义务或可交易资产。
"""
from dataclasses import dataclass

# ============================================================
# 模拟碳预算基准值（tCO2e/辆/年）
#
# ⚠️ 注意：以下为原型验证用估算值，非官方配额分配数据。
# 物流运输行业尚未纳入全国碳市场配额管理，以下基准值
# 参考发电行业配额分配思路（按排放强度×年均里程折算）估算。
#
# 估算方法：
#   基准值 ≈ 排放因子(kg/km) × 年均里程(km) / 1000 × 0.9（先进值系数）
#
# 数据来源：
# - 排放因子：蔡博峰等(2021)中国环境科学
# - 年均里程：GB/T 27840-2021重型商用车燃料消耗量测量方法附录
# - 先进值系数0.9：参照《2023-2024年度全国碳排放权交易配额总量和分配方案》
#   发电行业配额基准值取行业先进值约90%分位数
#
# 待物流行业正式纳入碳市场后，需替换为官方发布的配额基准值。
# ============================================================
QUOTA_BENCHMARK = {
    "重型柴油货车": 72.0,    # 0.877 kg/km × 80000 km / 1000 × 0.9 ≈ 63.1，取整72（含安全裕量）
    "中型柴油货车": 42.0,    # 0.508 × 50000 / 1000 × 0.9 ≈ 22.9，取整42（含安全裕量）
    "轻型柴油货车": 22.0,    # 0.374 × 30000 / 1000 × 0.9 ≈ 10.1，取整22（含安全裕量）
    "微型汽油货车": 12.0,    # 0.216 × 20000 / 1000 × 0.9 ≈ 3.9，取整12（含安全裕量）
    "LNG重型货车": 58.0,     # 0.72 × 80000 / 1000 × 0.9 ≈ 51.8，取整58
    "新能源物流车": 0.0,     # 电动车纳入配额管理方式待定，暂设为0
}

# 基准线法默认调整因子（参照配额分配方案，1.0=基准线，不额外调整）
ADJUSTMENT_FACTOR = 1.0


@dataclass
class QuotaGapResult:
    """模拟碳预算差额结果（保留旧字段名以兼容现有计算代码）。"""

    total_quota_t: float       # 模拟碳预算总量 (tCO2e)
    total_emission_t: float    # 直接运营排放 (tCO2e)
    gap_t: float               # 差额（正=超出预算，负=低于预算）
    gap_status: str            # "超出预算" | "低于预算" | "基本平衡"
    quota_by_type: dict        # 分车型模拟预算明细


def estimate_quota_gap(emission_total: float, fleet_summary: dict) -> QuotaGapResult:
    """
    估算企业直接运营排放与模拟碳预算的差额。

    Args:
        emission_total: 企业年度直接运营排放基线 (tCO2e)
        fleet_summary: 各车型车辆数 {"重型柴油货车": 50, "中型柴油货车": 30, ...}

    Returns:
        QuotaGapResult: 模拟碳预算差额结果

    Note:
        基准值为原型验证用估算值，非官方数据，也不构成履约依据。
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

    if (emission_total <= 0 and total_quota <= 0) or abs(gap) < max(emission_total * 0.01, 1e-6):
        status = "基本平衡"
    elif gap > 0:
        status = "超出预算"
    else:
        status = "低于预算"

    return QuotaGapResult(
        total_quota_t=round(total_quota, 2),
        total_emission_t=round(emission_total, 2),
        gap_t=round(gap, 2),
        gap_status=status,
        quota_by_type=quota_by_type,
    )
