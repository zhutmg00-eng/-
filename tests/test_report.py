"""PDF 报告关键字段与口径测试。"""

import fitz

from src.engine.carbon_price import estimate_compliance_cost
from src.ui.components.report import generate_carbon_report


def test_report_uses_budget_value_and_research_disclaimer(tmp_path):
    output = tmp_path / "report.pdf"
    report_path = generate_carbon_report(
        company_name="测试物流公司",
        total_emission_t=3508.0,
        total_vehicles=50,
        emission_by_type={
            "重型柴油货车": {
                "排放量_tCO2": 3508.0,
                "占比": 100.0,
                "车辆数": 50,
                "排放因子_kg_per_km": 0.877,
                "燃料类型": "柴油",
            }
        },
        total_quota_t=3157.2,
        gap_t=350.8,
        gap_status="超出预算",
        compliance_cost=estimate_compliance_cost(350.8),
        output_path=str(output),
    )

    document = fitz.open(report_path)
    text = "\n".join(page.get_text() for page in document)

    assert len(document) == 3
    assert "3,157.20" in text
    assert "-350.80" not in text
    assert "10%" in text
    assert "科研原型" in text
    assert "可交易资产" in text
    assert "购电间接排放" in text
    assert "第 1 页" in text
    assert "tCO₂" not in text
