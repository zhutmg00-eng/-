"""碳价参考与模拟碳预算情景成本估算。

成本计算公式：
    Cost = max(Gap, 0) × P_current
    成本区间: [Gap × P_min(90d), Gap × P_max(90d)]
"""
try:
    import pandas as pd
except ImportError:
    pd = None
from typing import Optional, Any


def load_carbon_price_data(csv_path: str = None) -> Any:
    """
    加载碳价历史数据

    Args:
        csv_path: CSV文件路径。如果未提供，尝试默认路径。

    Returns:
        DataFrame或None（文件不存在或pandas未安装时）
    """
    if pd is None:
        return None
    from src.config import RAW_DIR
    path = csv_path or str(RAW_DIR / "carbon_price_history.csv")

    try:
        df = pd.read_csv(path, parse_dates=["日期"])
        df = df.sort_values("日期")
        return df
    except Exception:
        return None


def calculate_price_stats(df) -> dict:
    """
    计算碳价统计指标

    Args:
        df: 碳价历史数据，需包含'收盘价'列

    Returns:
        dict: 统计指标
    """
    if df is None or df.empty:
        return {}

    recent = df[df["日期"] >= df["日期"].max() - pd.Timedelta(days=90)]
    return {
        "当前价": round(df["收盘价"].iloc[-1], 2),
        "近90日均价": round(recent["收盘价"].mean(), 2),
        "近90日最高": round(recent["收盘价"].max(), 2),
        "近90日最低": round(recent["收盘价"].min(), 2),
        "波动率(%)": round(recent["收盘价"].pct_change().std() * 100, 2),
    }


def estimate_compliance_cost(gap_t: float, price_df=None) -> dict:
    """
    基于历史碳价估算模拟预算差额的情景成本或潜在价值。

    函数名为兼容现有调用保留；结果不代表物流企业的法定履约成本、
    可交易配额或确定收益。

    Args:
        gap_t: 模拟碳预算差额 (tCO2e)，正数为超出预算
        price_df: 碳价历史数据DataFrame。如果None，使用模拟数据。

    Returns:
        dict: 成本估算结果
    """
    # 如果没有真实数据，使用模拟参考价
    if price_df is None or (pd is not None and price_df.empty):
        # 模拟参考价（基于2024-2025年全国碳市场大致区间）
        current_price = 70.0  # 元/吨
        avg_price = 68.0
        min_price = 55.0
        max_price = 85.0
        volatility = 8.5
    else:
        recent = price_df["收盘价"].tail(90)
        current_price = round(recent.iloc[-1], 2)
        avg_price = round(recent.mean(), 2)
        min_price = round(recent.min(), 2)
        max_price = round(recent.max(), 2)
        volatility = round(recent.pct_change().std() * 100, 2)

    if gap_t <= 0:
        judgement = "基本平衡" if abs(gap_t) < 1e-9 else "低于模拟碳预算"
        return {
            "情景判断": judgement,
            "预算结余_t": round(abs(gap_t), 2),
            "潜在价值_low": round(abs(gap_t) * min_price, 2),
            "潜在价值_high": round(abs(gap_t) * max_price, 2),
            "参考碳价_元每吨": current_price,
            "备注": "仅按全国碳市场价格估算潜在价值，不代表可交易配额或实际收益",
        }

    return {
        "情景判断": "超出模拟碳预算",
        "预算差额_t": round(gap_t, 2),
        "当前碳价_元每吨": current_price,
        "近90日均价_元每吨": avg_price,
        "碳价波动率": f"{volatility}%",
        "情景成本_参考价": round(gap_t * current_price, 2),
        "情景成本区间_low": round(gap_t * min_price, 2),
        "情景成本区间_high": round(gap_t * max_price, 2),
        "备注": "科研情景估算，不代表物流企业当前存在碳市场履约义务",
    }
