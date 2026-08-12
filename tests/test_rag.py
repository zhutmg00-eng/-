"""RAG模块测试"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.parser import clean_policy_text, chunk_policy_text


class TestParser:
    def test_clean_removes_empty_lines(self):
        """清洗应移除空行"""
        raw = "第一行\n\n\n第二行\n\n第三行"
        cleaned = clean_policy_text(raw)
        assert "\n\n" not in cleaned

    def test_chunk_size(self):
        """chunk大小不超过设定值太多"""
        text = "这是一段很长的政策文本。" * 200
        chunks = chunk_policy_text(text, chunk_size=800, overlap=150)
        for chunk in chunks:
            assert len(chunk["text"]) <= 1000  # 允许少量超出

    def test_chunk_metadata(self):
        """chunk应包含元数据"""
        text = "政策内容第一条。\n政策内容第二条。"
        chunks = chunk_policy_text(text, doc_source="test.pdf", doc_date="2024-01-01")
        for chunk in chunks:
            assert chunk["metadata"]["source"] == "test.pdf"
            assert chunk["metadata"]["date"] == "2024-01-01"

    def test_chunk_overlap(self):
        """相邻chunk应有重叠"""
        text = "A" * 1000
        chunks = chunk_policy_text(text, chunk_size=400, overlap=100)
        if len(chunks) >= 2:
            # 第二个chunk的开头应与第一个chunk的结尾有重叠
            assert chunks[1]["text"][:50] in chunks[0]["text"]


class TestVectorStore:
    def test_init(self):
        """向量库应能初始化"""
        from src.rag.vector_store import PolicyVectorStore
        vs = PolicyVectorStore(persist_dir="/tmp/test_chroma_db")
        stats = vs.get_stats()
        assert "total_chunks" in stats
        # 清理
        import shutil
        shutil.rmtree("/tmp/test_chroma_db", ignore_errors=True)
