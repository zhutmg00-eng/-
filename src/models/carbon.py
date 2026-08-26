"""直接运营排放与模拟碳预算数据模型。"""
from pydantic import BaseModel, Field
from typing import Optional


class CarbonBaseline(BaseModel):
    """碳排放基线计算结果"""
    total_emission_t: float = Field(..., description="年度直接运营排放总量 (tCO2e)")
    emission_by_type: dict = Field(default_factory=dict, description="分车型排放明细")
    total_vehicles: int = Field(..., description="总车辆数")


class CarbonBudget(BaseModel):
    """模拟碳预算差额结果。"""

    total_budget_t: float = Field(..., description="模拟碳预算总量 (tCO2e)")
    total_emission_t: float = Field(..., description="直接运营排放 (tCO2e)")
    gap_t: float = Field(..., description="差额（正=超出预算，负=低于预算）")
    status: str = Field(..., description="状态：超出预算/低于预算/基本平衡")


class ScenarioCost(BaseModel):
    """碳价对标情景金额。"""

    judgement: str = Field(..., description="情景判断")
    gap_t: Optional[float] = Field(None, description="模拟碳预算差额")
    current_price: Optional[float] = Field(None, description="当前碳价")
    avg_price_90d: Optional[float] = Field(None, description="近90日均价")
    cost_estimate: Optional[float] = Field(None, description="情景成本参考值")
    cost_low: Optional[float] = Field(None, description="成本下限")
    cost_high: Optional[float] = Field(None, description="成本上限")
    notes: Optional[str] = Field(None, description="备注")


class CarbonResult(BaseModel):
    """完整碳排放计算结果"""
    company_name: str
    total_emission_t: float
    total_vehicles: int
    emission_by_type: dict
    carbon_budget: dict
    scenario_cost: dict
    methodology_note: str


# 兼容早期导入名称；新代码应使用 CarbonBudget 和 ScenarioCost。
QuotaGap = CarbonBudget
ComplianceCost = ScenarioCost
