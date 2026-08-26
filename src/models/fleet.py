"""API 共用的车队输入模型。"""

from pydantic import BaseModel, Field, field_validator

from src.engine.emission_factors import get_emission_factor


class VehicleInput(BaseModel):
    """一组同类型车辆。"""

    vehicle_type: str = Field(..., min_length=1, description="车型名称")
    count: int = Field(..., gt=0, description="车辆数量（辆）")
    annual_km: float = Field(..., gt=0, description="年均运营里程 (km/年)")
    load_factor: float = Field(0.75, ge=0, le=1, description="平均满载率 (0~1)")

    @field_validator("vehicle_type")
    @classmethod
    def validate_vehicle_type(cls, value: str) -> str:
        vehicle_type = value.strip()
        if not get_emission_factor(vehicle_type):
            raise ValueError(f"不支持的车型: {vehicle_type or value}")
        return vehicle_type


class FleetInput(BaseModel):
    """企业车队输入。"""

    company_name: str = Field(..., min_length=1, max_length=100, description="企业名称")
    fleet: list[VehicleInput] = Field(..., min_length=1, description="车队分组列表")
    scenario_reduction_target: float = Field(
        0.10,
        ge=0,
        lt=1,
        description="模拟预算相对参考活动排放的减排目标（科研情景参数）",
    )

    @field_validator("company_name")
    @classmethod
    def normalize_company_name(cls, value: str) -> str:
        company_name = value.strip()
        if not company_name:
            raise ValueError("企业名称不能为空")
        return company_name


# 兼容早期代码中的名称。
VehicleGroup = VehicleInput
