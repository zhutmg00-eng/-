"""FastAPI 后端服务入口"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(
    title="碳资产管理与智能合规决策助手 API",
    version="0.1.0",
    description="面向物流企业的碳资产管理工具",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== 数据模型 ==========

class VehicleInput(BaseModel):
    vehicle_type: str
    count: int
    annual_km: float
    load_factor: float = 0.75

class FleetInput(BaseModel):
    company_name: str
    fleet: List[VehicleInput]

class CarbonResult(BaseModel):
    company_name: str
    total_emission_t: float
    total_vehicles: int
    emission_by_type: dict
    quota_gap: dict
    compliance_cost: dict

class PolicyQuestion(BaseModel):
    question: str
    carbon_profile: dict

class PolicyAnswer(BaseModel):
    question: str
    retrieved_sources: List[dict]
    answer: str


# ========== API路由 ==========

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/vehicle-types")
async def get_vehicle_types():
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
async def calculate_carbon(fleet_input: FleetInput):
    """计算企业碳排放基线、配额缺口、合规成本"""
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

    # 3. 构建车队摘要 → 估算配额缺口
    fleet_summary = {}
    for v in fleet_input.fleet:
        fleet_summary[v.vehicle_type] = fleet_summary.get(v.vehicle_type, 0) + v.count

    gap = estimate_quota_gap(baseline.total_emission_t, fleet_summary)

    # 4. 加载碳价数据 → 估算成本
    price_df = load_carbon_price_data()
    cost = estimate_compliance_cost(gap.gap_t, price_df)

    return CarbonResult(
        company_name=fleet_input.company_name,
        total_emission_t=baseline.total_emission_t,
        total_vehicles=baseline.total_vehicles,
        emission_by_type=baseline.emission_by_type,
        quota_gap={
            "配额总量_t": gap.total_quota_t,
            "缺口_t": gap.gap_t,
            "状态": gap.gap_status,
            "分车型配额": gap.quota_by_type,
        },
        compliance_cost=cost,
    )


@app.post("/api/ask", response_model=PolicyAnswer)
async def ask_policy(question: PolicyQuestion):
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
async def kb_stats():
    """知识库统计"""
    from src.rag.vector_store import PolicyVectorStore
    vs = PolicyVectorStore()
    return vs.get_stats()


@app.post("/api/kb/ingest")
async def ingest_document(file_path: str, doc_date: str = ""):
    """导入一份政策文档到知识库"""
    from src.rag import PolicyAdvisor
    advisor = PolicyAdvisor()
    count = advisor.ingest_document(file_path, doc_date)
    return {"file": file_path, "chunks_added": count}
