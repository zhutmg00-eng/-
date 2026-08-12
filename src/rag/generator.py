"""LLM调用与Prompt模板引擎"""
from typing import List, Dict
from src.config import LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS, get_llm_config

# ============================================================
# Prompt模板
# ============================================================

SYSTEM_PROMPT = """你是一位专业的碳交易政策顾问，服务于物流运输企业。
你的职责是：基于提供的政策条款（检索结果）和企业数据（碳画像），为企业生成准确、可操作的碳合规建议。

请遵循以下原则：
1. 只基于提供的政策条款内容作答，不要编造信息
2. 如果检索到的政策条款不足以回答用户问题，请明确说明"根据当前检索结果，无法确定..."
3. 引用政策时，注明来源文件名和发布日期
4. 建议应具体、可执行，避免空泛的"应加强管理"类表述
5. 回答格式：【政策依据】→【适用情况分析】→【建议措施】→【风险提示】"""


def build_user_prompt(
    user_question: str,
    retrieved_chunks: List[Dict],
    carbon_profile: dict,
) -> str:
    """
    构建发送给LLM的完整用户Prompt

    结构：
    1. 检索到的政策条款（作为上下文）
    2. 企业碳画像（碳排放数据）
    3. 用户问题
    """
    # 组装检索上下文
    context_parts = []
    for i, chunk in enumerate(retrieved_chunks, 1):
        source = chunk.get("metadata", {}).get("source", "未知来源")
        date = chunk.get("metadata", {}).get("date", "")
        date_str = f" ({date})" if date else ""
        context_parts.append(
            f"[参考条款{i}] 来源: {source}{date_str}\n{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_parts) if context_parts else "（未检索到相关政策条款）"

    # 组装企业碳画像
    profile_str = f"""企业类型: {carbon_profile.get('企业类型', '物流运输企业')}
车队规模: {carbon_profile.get('总车辆数', '未知')} 辆
年度碳排放基线: {carbon_profile.get('年度碳排放_t', '未知')} tCO₂
碳配额缺口: {carbon_profile.get('配额缺口_t', '未知')} tCO₂
缺口状态: {carbon_profile.get('缺口状态', '未知')}
预估碳合规成本: {carbon_profile.get('预估成本_元', '未知')} 元"""

    return f"""请根据以下政策条款，结合该企业的碳资产状况，回答企业的问题。

====== 相关碳交易政策条款 ======
{context}

====== 企业碳资产状况 ======
{profile_str}

====== 企业问题 ======
{user_question}

请按以下格式回答：
【政策依据】列出适用的政策条款（注明来源文件名）
【适用情况分析】结合该企业的具体排放数据和配额状况分析
【建议措施】给出具体可执行的合规建议
【风险提示】提醒潜在的合规风险和注意事项"""


def call_llm(
    system_prompt: str,
    user_prompt: str,
    model: str = None,
    temperature: float = None,
) -> str:
    """
    调用大语言模型API

    支持的模型：deepseek-chat / qwen-turbo / glm-4-flash
    """
    from openai import OpenAI

    model = model or LLM_MODEL
    temperature = temperature if temperature is not None else LLM_TEMPERATURE
    config = get_llm_config(model)

    client = OpenAI(
        api_key=config["api_key"],
        base_url=config["base_url"],
    )

    response = client.chat.completions.create(
        model=config["model"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=LLM_MAX_TOKENS,
    )

    return response.choices[0].message.content
