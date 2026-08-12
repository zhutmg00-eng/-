#!/usr/bin/env python3
"""RAG端到端测试 — 关键词检索模式

测试链路：政策文档 → 入库 → 检索 → 构建Prompt → （模拟）生成
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.parser import chunk_policy_text, clean_policy_text
from src.rag.vector_store import PolicyVectorStore
from src.rag.generator import build_user_prompt, SYSTEM_PROMPT

def test_rag_pipeline():
    print("=" * 60)
    print("🔍 RAG端到端测试（关键词检索模式）")
    print("=" * 60)

    # === 1. 初始化知识库 ===
    print("\n📋 步骤1: 初始化知识库")
    vs = PolicyVectorStore()
    stats = vs.get_stats()
    print(f"  模式: {stats['mode']}")
    print(f"  文档块数: {stats['total_chunks']}")

    # === 2. 导入几份关键政策文档 ===
    if stats['total_chunks'] == 0:
        print("\n📋 步骤2: 导入政策文档")
        policy_dir = Path(__file__).parent.parent / "data" / "policy_docs"

        # 选择几份核心文档
        key_docs = [
            "碳排放权交易管理暂行条例.md",
            "碳排放权交易管理办法_试行_全文.md",
            "交通运输碳达峰实施方案.md",
            "温室气体自愿减排交易管理办法_试行.md",
            "2025年全国碳市场有关工作通知.md",
            "推进绿色低碳转型加强全国碳市场建设意见_2025.md",
            "十五五碳达峰行动方案_2026.md",
            "企业温室气体排放核算与报告指南_发电设施.md",
        ]
        total_chunks = 0
        for doc_name in key_docs:
            doc_path = policy_dir / doc_name
            if not doc_path.exists():
                print(f"  ⏭️  跳过: {doc_name}（不存在）")
                continue

            text = doc_path.read_text(encoding="utf-8")
            if len(text) < 100:
                continue

            # 清洗+切分
            cleaned = clean_policy_text(text)
            chunks = chunk_policy_text(cleaned, doc_source=doc_name, doc_date="2025")

            vs.add_documents(chunks, doc_name, "2025")
            total_chunks += len(chunks)
            print(f"  ✅ {doc_name}: {len(chunks)} chunks")

        print(f"\n  总计导入: {total_chunks} 个文档块")
        stats = vs.get_stats()
        print(f"  知识库: {stats['total_chunks']} 个文档块 ({stats['mode']})")
    else:
        print(f"\n📋 步骤2: 跳过（已有 {stats['total_chunks']} 个文档块）")

    # === 3. 测试检索 ===
    print("\n📋 步骤3: 检索测试")

    test_queries = [
        "物流企业碳排放怎么计算",
        "碳配额不够怎么办，需要购买吗",
        "碳交易市场罚款标准是什么",
        "交通运输行业碳达峰目标",
        "企业如何进行温室气体排放报告",
        "CCER自愿减排量怎么用",
    ]

    for query in test_queries:
        print(f"\n  ❓ {query}")
        results = vs.search(query, k=3)
        for i, r in enumerate(results, 1):
            source = r["metadata"].get("source", "未知")
            score = r.get("distance", 1)
            text_preview = r["text"][:120].replace("\n", " ")
            print(f"    [{i}] {source} (score={score:.3f})")
            print(f"        {text_preview}...")

    # === 4. 测试Prompt构建 ===
    print("\n📋 步骤4: Prompt构建测试")

    query = "我们公司有50辆重型柴油货车，年排放约3500吨CO₂，配额够用吗？"
    results = vs.search(query, k=3)

    carbon_profile = {
        "企业类型": "物流运输企业",
        "总车辆数": 50,
        "年度碳排放_t": 3500,
        "配额缺口_t": 200,
        "缺口状态": "缺口",
        "预估成本_元": 15000,
    }

    user_prompt = build_user_prompt(query, results, carbon_profile)

    print(f"\n  用户问题: {query}")
    print(f"  检索结果: {len(results)} 个chunk")
    print(f"  Prompt长度: {len(user_prompt)} 字符")
    print(f"\n  --- System Prompt (前200字) ---")
    print(f"  {SYSTEM_PROMPT[:200]}...")
    print(f"\n  --- User Prompt (前500字) ---")
    print(f"  {user_prompt[:500]}...")

    # === 5. 模拟LLM生成 ===
    print("\n📋 步骤5: 模拟LLM生成（规则模板）")

    # 不调用真实LLM，用规则模板模拟
    mock_response = generate_mock_response(query, results, carbon_profile)
    print(f"\n  📝 模拟合规建议:")
    print(mock_response)

    print("\n" + "=" * 60)
    print("✅ RAG端到端测试完成（关键词检索模式）")
    print("=" * 60)
    print("""
    注意：当前使用TF-IDF关键词检索模式（ChromaDB未安装）。
    团队本地安装chromadb后，运行 ingest_policy_docs.py 即可切换到语义检索模式。
    """)


def generate_mock_response(query: str, chunks: list, profile: dict) -> str:
    """模拟LLM生成（不调用API）"""
    sources = [c["metadata"].get("source", "") for c in chunks[:3]]

    response = f"""【政策依据】
"""
    for s in sources:
        response += f"  - {s}\n"

    response += f"""
【适用情况分析】
该企业为物流运输企业，拥有{profile.get('总车辆数', '未知')}辆车辆，
年度碳排放约{profile.get('年度碳排放_t', '未知')} tCO₂，
配额缺口约{profile.get('配额缺口_t', '未知')} tCO₂，
预估合规成本约{profile.get('预估成本_元', '未知')}元。

【建议措施】
1. 按照碳排放权交易管理办法要求，及时制定年度数据质量控制方案
2. 每月结束后40个自然日内完成碳排放统计核算数据月度信息化存证
3. 3月31日前报送年度温室气体排放报告
4. 12月31日前完成配额清缴
5. 可考虑购买CCER核证自愿减排量抵销部分配额清缴
6. 优化车队结构，增加新能源车辆比例

【风险提示】
1. 未按时足额清缴配额将面临罚款（暂行条例规定）
2. 数据弄虚作假将被严厉处罚
3. 碳价波动风险，建议提前锁定价格
"""
    return response


if __name__ == "__main__":
    test_rag_pipeline()
