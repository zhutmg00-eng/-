"""FastAPI 后端服务入口

安全措施：
- CORS限制为可信来源（可通过环境变量配置）
- API key鉴权（X-API-Key header）
- 文件路径校验（防止路径遍历攻击）
"""
import os
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path

from src.models.fleet import FleetInput
from src.models.policy import PolicyAnswer, PolicyQuestion

app = FastAPI(
    title="物流碳排放与减排情景决策助手 API",
    version="0.3.0",
    description="面向物流企业的科研原型，核算直接运营排放并模拟减排情景",
)


# ============================================================
# CORS配置（可通过环境变量配置允许的来源）
# ============================================================
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8501,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ============================================================
# API Key鉴权
# ============================================================
API_KEY = os.getenv("APP_API_KEY", "")  # 不设则为开发模式（不鉴权）
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    """验证API Key（如果配置了APP_API_KEY则强制校验，否则开发模式跳过）"""
    if API_KEY:  # 生产模式：需要校验
        if api_key != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
    # 开发模式（未设API_KEY）：跳过鉴权
    return api_key


# ============================================================
# 安全路径校验
# ============================================================
def safe_resolve_path(file_path: str, base_dir: Path) -> Path:
    """安全解析文件路径，防止路径遍历攻击"""
    base_dir = base_dir.resolve()
    requested = Path(file_path).resolve()
    # 确保解析后的路径在base_dir内
    if not requested.is_relative_to(base_dir):
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: path must be within {base_dir}"
        )
    return requested


# ============================================================
# 注册路由
# ============================================================
from src.api.routes_compare import router as compare_router
app.include_router(compare_router)


# ========== 数据模型 ==========

class CarbonResult(BaseModel):
    company_name: str
    total_emission_t: float
    total_vehicles: int
    emission_by_type: dict
    carbon_budget: dict
    scenario_cost: dict
    methodology_note: str

# ========== API路由 ==========

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "0.3.0"}


@app.get("/api/vehicle-types")
async def get_vehicle_types(api_key: str = Depends(verify_api_key)):
    """获取支持的车型列表"""
    from src.engine.emission_factors import list_vehicle_types, get_all_factors
    factors = get_all_factors()
    return {
        "vehicle_types": [
            {
                "name": name,
                "fuel_type": data["fuel_type"],
                "co2_kg_per_km": data["co2_kg_per_km"],
                "avg_annual_km": data["avg_annual_km"],
            }
            for name, data in factors.items()
        ]
    }


@app.post("/api/calculate", response_model=CarbonResult)
async def calculate_carbon(fleet_input: FleetInput, api_key: str = Depends(verify_api_key)):
    """计算直接运营排放基线、模拟碳预算差额和情景成本。"""
    from src.engine.calculator import VehicleGroupData, calculate_emission
    from src.engine.quota import estimate_quota_gap
    from src.engine.carbon_price import estimate_compliance_cost, load_carbon_price_data

    # 1. 转换输入
    fleet = [
        VehicleGroupData(
            vehicle_type=v.vehicle_type,
            count=v.count,
            annual_km=v.annual_km,
            load_factor=v.load_factor,
        )
        for v in fleet_input.fleet
    ]

    # 2. 计算碳排放基线
    baseline = calculate_emission(fleet)

    # 3. 构建车队摘要 → 估算模拟碳预算差额
    fleet_summary = {}
    for v in fleet_input.fleet:
        fleet_summary[v.vehicle_type] = fleet_summary.get(v.vehicle_type, 0) + v.count

    gap = estimate_quota_gap(
        baseline.total_emission_t,
        fleet_summary,
        reduction_target=fleet_input.scenario_reduction_target,
    )

    # 4. 加载碳价数据 → 估算成本
    price_df = load_carbon_price_data()
    cost = estimate_compliance_cost(gap.gap_t, price_df)

    return CarbonResult(
        company_name=fleet_input.company_name,
        total_emission_t=baseline.total_emission_t,
        total_vehicles=baseline.total_vehicles,
        emission_by_type=baseline.emission_by_type,
        carbon_budget={
            "模拟碳预算_t": gap.total_quota_t,
            "预算差额_t": gap.gap_t,
            "状态": gap.gap_status,
            "分车型预算": gap.quota_by_type,
            "情景减排目标": gap.reduction_target,
            "口径说明": "科研原型估算，不是法定配额或履约依据",
        },
        scenario_cost=cost,
        methodology_note=(
            "当前仅核算车辆直接运营排放；新能源物流车的购电间接排放及车辆全生命周期排放未计入。"
        ),
    )


@app.post("/api/ask", response_model=PolicyAnswer)
async def ask_policy(question: PolicyQuestion, api_key: str = Depends(verify_api_key)):
    """碳交易政策智能问答"""
    from src.rag import PolicyAdvisor

    advisor = PolicyAdvisor()
    result = advisor.ask(question.question, question.carbon_profile)

    return PolicyAnswer(
        question=result["question"],
        retrieved_sources=result["retrieved_sources"],
        answer=result["answer"],
    )


@app.get("/api/kb/stats")
async def kb_stats(api_key: str = Depends(verify_api_key)):
    """知识库统计"""
    from src.rag.vector_store import PolicyVectorStore
    vs = PolicyVectorStore()
    return vs.get_stats()


@app.post("/api/kb/ingest")
async def ingest_document(
    file_path: str,
    doc_date: str = "",
    api_key: str = Depends(verify_api_key),
):
    """导入一份政策文档到知识库

    安全措施：file_path必须位于项目data目录内，防止路径遍历攻击
    """
    from src.config import POLICY_DOCS_DIR
    from src.rag import PolicyAdvisor

    # 安全校验：确保文件路径在policy_docs目录内
    safe_path = safe_resolve_path(file_path, POLICY_DOCS_DIR)
    if not safe_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    advisor = PolicyAdvisor()
    count = advisor.ingest_document(str(safe_path), doc_date)
    return {"file": safe_path.name, "chunks_added": count}
