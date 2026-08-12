"""碳排放与配额数据模型"""
from pydantic import BaseModel, Field
from typing import Optional


class CarbonBaseline(BaseModel):
    """碳排放基线计算结果"""
    total_emission_t: float = Field(..., description="年度碳排放总量 (tCO₂)")
    emission_by_type: dict = Field(default_factory=dict, description="分车型排放明细")
    total_vehicles: int = Field(..., description="总车辆数")


class QuotaGap(BaseModel):
    """配额缺口结果"""
    total_quota_t: float = Field(..., description="免费配额总量 (tCO₂)")
    total_emission_t: float = Field(..., description="实际排放 (tCO₂)")
    gap_t: float = Field(..., description="缺口（正=需购买，负=盈余）")
    gap_status: str = Field(..., description="状态：缺口/盈余/平衡")


class ComplianceCost(BaseModel):
    """合规成本估算"""
    demand: str = Field(..., description="合规需求类型")
    gap_t: Optional[float] = Field(None, description="配额缺口")
    current_price: Optional[float] = Field(None, description="当前碳价")
    avg_price_90d: Optional[float] = Field(None, description="近90日均价")
    cost_estimate: Optional[float] = Field(None, description="预估合规成本")
    cost_low: Optional[float] = Field(None, description="成本下限")
    cost_high: Optional[float] = Field(None, description="成本上限")
    notes: Optional[str] = Field(None, description="备注")


class CarbonResult(BaseModel):
    """完整碳排放计算结果"""
    company_name: str
    total_emission_t: float
    total_vehicles: int
    emission_by_type: dict
    quota_gap: dict
    compliance_cost: dict
