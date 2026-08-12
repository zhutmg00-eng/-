"""车队数据模型"""
from pydantic import BaseModel, Field
from typing import Optional


class VehicleGroup(BaseModel):
    """一组同类型车辆"""
    vehicle_type: str = Field(..., description="车型名称")
    fuel_type: str = Field(..., description="燃料类型：柴油/汽油/LNG/电动")
    count: int = Field(..., gt=0, description="车辆数量（辆）")
    annual_km: float = Field(..., gt=0, description="年均运营里程 (km/年)")
    load_factor: float = Field(0.75, ge=0, le=1, description="平均满载率 (0~1)")


class FleetInput(BaseModel):
    """企业车队输入"""
    company_name: str = Field(..., description="企业名称")
    fleet: list[VehicleGroup] = Field(..., description="车队分组列表")
