"""多企业碳资产对比 API 路由

提供多企业并排对比功能，输入多个企业车队数据，输出：
- 排放总量对比
- 配额缺口对比
- 合规成本对比及排序

所有计算复用 engine 层现有引擎。
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import List
from pydantic import BaseModel, Field

from src.api.main import verify_api_key

router = APIRouter(prefix="/api", tags=["多企业对比"])


# ============================================================
# 请求/响应模型
# ============================================================

class CompareFleetInput(BaseModel):
    """对比用企业车队输入"""
    company_name: str = Field(..., description="企业名称")
    fleet: list = Field(..., description="车队分组列表")
    # fleet 格式：[{"vehicle_type": str, "count": int, "annual_km": float, "load_factor": float}]


class CompareRequest(BaseModel):
    """多企业对比请求"""
    companies: List[CompareFleetInput] = Field(
        ...,
        min_length=2,
        description="至少2个企业车队数据"
    )


class EnterpriseCompareResult(BaseModel):
    """单个企业的对比结果"""
    company_name: str
    total_emission_t: float
    total_vehicles: int
    emission_by_type: dict
    quota_total_t: float
    quota_gap_t: float
    quota_status: str
    compliance_cost: dict


class CompareResponse(BaseModel):
    """多企业对比响应"""
    comparison: List[EnterpriseCompareResult]
    ranking_by_emission: List[str]  # 按排放降序排列的企业名
    ranking_by_gap: List[str]  # 按配额缺口降序排列的企业名
    ranking_by_cost: List[str]  # 按合规成本降序排列的企业名
    summary: dict  # 汇总统计


# ============================================================
# API 路由
# ============================================================

@router.post("/compare", response_model=CompareResponse)
async def compare_enterprises(
    request: CompareRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    对比多个企业的碳资产数据

    输入多个企业车队数据，输出并排对比：
    - 排放总量、配额缺口、合规成本
    - 多维度排序（排放量、缺口、成本）
    - 汇总统计

    示例请求：
        POST /api/compare
        {
            "companies": [
                {
                    "company_name": "A物流公司",
                    "fleet": [
                        {"vehicle_type": "重型柴油货车", "count": 50, "annual_km": 80000, "load_factor": 0.7},
                        {"vehicle_type": "轻型柴油货车", "count": 30, "annual_km": 30000}
                    ]
                },
                {
                    "company_name": "B物流公司",
                    "fleet": [
                        {"vehicle_type": "重型柴油货车", "count": 30, "annual_km": 80000},
                        {"vehicle_type": "新能源物流车", "count": 20, "annual_km": 40000}
                    ]
                }
            ]
        }
    """
    from src.engine.calculator import VehicleGroupData, calculate_emission
    from src.engine.quota import estimate_quota_gap
    from src.engine.carbon_price import estimate_compliance_cost, load_carbon_price_data

    # 验证至少2个企业
    if len(request.companies) < 2:
        raise HTTPException(status_code=400, detail="至少需要2个企业数据进行对比")

    # 加载碳价数据（所有企业共用同一碳价）
    price_df = load_carbon_price_data()

    results = []
    for company in request.companies:
        # 1. 转换输入为内部格式
        fleet = []
        fleet_summary = {}
        for v in company.fleet:
            vehicle_data = VehicleGroupData(
                vehicle_type=v["vehicle_type"],
                count=v["count"],
                annual_km=v.get("annual_km", 30000),
                load_factor=v.get("load_factor", 0.75),
            )
            fleet.append(vehicle_data)
            fleet_summary[v["vehicle_type"]] = fleet_summary.get(v["vehicle_type"], 0) + v["count"]

        # 2. 计算碳排放
        try:
            baseline = calculate_emission(fleet)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # 3. 估算配额缺口
        gap = estimate_quota_gap(baseline.total_emission_t, fleet_summary)

        # 4. 估算合规成本
        cost = estimate_compliance_cost(gap.gap_t, price_df)

        results.append(EnterpriseCompareResult(
            company_name=company.company_name,
            total_emission_t=baseline.total_emission_t,
            total_vehicles=baseline.total_vehicles,
            emission_by_type=baseline.emission_by_type,
            quota_total_t=gap.total_quota_t,
            quota_gap_t=gap.gap_t,
            quota_status=gap.gap_status,
            compliance_cost=cost,
        ))

    # 多维度排序
    ranking_emission = sorted(results, key=lambda x: x.total_emission_t, reverse=True)
    ranking_gap = sorted(results, key=lambda x: x.quota_gap_t, reverse=True)

    # 按合规成本排序（需购买配额的企业排在前面）
    def cost_key(r: EnterpriseCompareResult) -> float:
        cost_val = r.compliance_cost.get("预估合规成本_参考价", 0)
        return cost_val if cost_val > 0 else -1

    ranking_cost = sorted(results, key=cost_key, reverse=True)

    # 汇总统计
    total_emission = sum(r.total_emission_t for r in results)
    total_gap = sum(r.quota_gap_t for r in results)
    total_cost = sum(
        r.compliance_cost.get("预估合规成本_参考价", 0)
        for r in results
        if r.compliance_cost.get("预估合规成本_参考价", 0) > 0
    )

    summary = {
        "企业数量": len(results),
        "排放总量_tCO₂": round(total_emission, 2),
        "总配额缺口_tCO₂": round(total_gap, 2),
        "总合规成本_元": round(total_cost, 2),
        "排放最高企业": ranking_emission[0].company_name if ranking_emission else "",
        "缺口最大企业": ranking_gap[0].company_name if ranking_gap else "",
    }

    return CompareResponse(
        comparison=results,
        ranking_by_emission=[r.company_name for r in ranking_emission],
        ranking_by_gap=[r.company_name for r in ranking_gap],
        ranking_by_cost=[r.company_name for r in ranking_cost],
        summary=summary,
    )
