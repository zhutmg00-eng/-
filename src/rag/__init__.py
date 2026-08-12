"""RAG政策解析助手 - 完整调用链路"""
from src.rag.vector_store import PolicyVectorStore
from src.rag.generator import SYSTEM_PROMPT, build_user_prompt, call_llm
from src.config import RETRIEVAL_TOP_K


class PolicyAdvisor:
    """碳交易政策顾问"""

    def __init__(self, vector_store: PolicyVectorStore = None):
        self.vs = vector_store or PolicyVectorStore()

    def ask(
        self,
        question: str,
        carbon_profile: dict,
        top_k: int = None,
    ) -> dict:
        """
        单次问答

        Args:
            question: 用户自然语言问题
            carbon_profile: 企业碳画像数据
            top_k: 检索返回数量

        Returns:
            dict: {question, retrieved_sources, answer}
        """
        top_k = top_k or RETRIEVAL_TOP_K

        # 1. 检索
        retrieved = self.vs.search(question, k=top_k)

        # 2. 构建Prompt
        user_prompt = build_user_prompt(question, retrieved, carbon_profile)

        # 3. 调用LLM
        answer = call_llm(SYSTEM_PROMPT, user_prompt)

        return {
            "question": question,
            "retrieved_sources": [
                {
                    "source": r["metadata"].get("source", "未知"),
                    "date": r["metadata"].get("date", ""),
                    "relevance": round(1 - r.get("distance", 0), 3) if r.get("distance") else None,
                }
                for r in retrieved
            ],
            "answer": answer,
        }

    def ingest_document(self, file_path, doc_date: str = ""):
        """导入一份政策文档到知识库"""
        from src.rag.parser import process_document
        from pathlib import Path

        file_path = Path(file_path)
        chunks = process_document(file_path, doc_date)
        self.vs.add_documents(chunks, file_path.name, doc_date)
        return len(chunks)


__all__ = [
    "PolicyAdvisor",
    "PolicyVectorStore",
    "SYSTEM_PROMPT",
    "build_user_prompt",
    "call_llm",
]
