"""ChromaDB向量知识库管理

支持两种模式：
1. ChromaDB模式（推荐）：语义向量检索，需安装chromadb
2. 关键词模式（fallback）：TF-IDF关键词检索，无需额外依赖
"""
from typing import List, Dict, Optional
from pathlib import Path
import re
import math
from collections import Counter
from src.config import CHROMA_DB_DIR, EMBEDDING_MODEL

# 尝试导入chromadb
try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


class PolicyVectorStore:
    """碳交易政策向量知识库

    自动选择ChromaDB（已安装）或关键词检索（未安装）模式
    """

    def __init__(self, persist_dir: str = None):
        self.persist_dir = persist_dir or str(CHROMA_DB_DIR)
        self.collection_name = "carbon_policy"
        self._fallback_docs: List[Dict] = []  # 关键词模式的文档存储

        if CHROMA_AVAILABLE:
            self._init_chroma()
        else:
            self._init_fallback()

    def _init_chroma(self):
        """初始化ChromaDB"""
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        try:
            self.collection = self.client.get_collection(self.collection_name)
            print(f"✅ 已加载ChromaDB知识库: {self.collection.count()} 个文档块")
        except Exception:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "中国碳交易政策法规知识库"},
            )
            print("✅ 已创建新ChromaDB知识库")

    def _init_fallback(self):
        """初始化关键词检索模式"""
        # 尝试从JSON加载之前入库的文档
        import json
        cache_file = Path(self.persist_dir) / "fallback_docs.json"
        if cache_file.exists():
            self._fallback_docs = json.loads(cache_file.read_text(encoding="utf-8"))
            print(f"✅ 已加载关键词检索知识库: {len(self._fallback_docs)} 个文档块")
        else:
            print("✅ 已创建新关键词检索知识库（ChromaDB未安装）")

    def add_documents(self, chunks: List[Dict], doc_source: str, doc_date: str = ""):
        """向知识库添加文档chunk"""
        if not chunks:
            return

        if CHROMA_AVAILABLE:
            self._add_chroma(chunks, doc_source, doc_date)
        else:
            self._add_fallback(chunks, doc_source, doc_date)

    def _add_chroma(self, chunks: List[Dict], doc_source: str, doc_date: str = ""):
        """ChromaDB模式入库"""
        ids = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_source}_{i}"
            ids.append(chunk_id)
            documents.append(chunk["text"])
            metadatas.append({
                "source": doc_source,
                "date": doc_date,
                "chunk_index": i,
                **chunk.get("metadata", {}),
            })

        self.collection.add(ids=ids, documents=documents, metadatas=metadatas)
        print(f"✅ 已入库 {len(chunks)} 个文档块 来自: {doc_source}")

    def _add_fallback(self, chunks: List[Dict], doc_source: str, doc_date: str = ""):
        """关键词模式入库"""
        import json
        for i, chunk in enumerate(chunks):
            self._fallback_docs.append({
                "id": f"{doc_source}_{i}",
                "text": chunk["text"],
                "metadata": {
                    "source": doc_source,
                    "date": doc_date,
                    "chunk_index": i,
                    **chunk.get("metadata", {}),
                },
            })

        # 持久化到JSON
        cache_file = Path(self.persist_dir) / "fallback_docs.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(
            json.dumps(self._fallback_docs, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"✅ 已入库 {len(chunks)} 个文档块 来自: {doc_source}")

    def search(self, query: str, k: int = 5) -> List[Dict]:
        """语义检索最相关的政策条款"""
        if CHROMA_AVAILABLE:
            return self._search_chroma(query, k)
        else:
            return self._search_tfidf(query, k)

    def _search_chroma(self, query: str, k: int = 5) -> List[Dict]:
        """ChromaDB语义检索"""
        results = self.collection.query(query_texts=[query], n_results=k)

        formatted = []
        if results["documents"] and results["documents"][0]:
            for i in range(len(results["documents"][0])):
                formatted.append({
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else None,
                })
        return formatted

    def _search_tfidf(self, query: str, k: int = 5) -> List[Dict]:
        """TF-IDF关键词检索（fallback模式）

        简单但有效的中文文本检索：
        1. 对query进行字符级n-gram分词（2-4 gram）
        2. 计算TF-IDF相似度
        3. 返回Top-K结果
        """
        if not self._fallback_docs:
            return []

        # 生成n-gram
        def get_ngrams(text: str, n: int = 2) -> List[str]:
            text = re.sub(r"\s+", "", text)
            return [text[i:i+n] for i in range(len(text) - n + 1)] if len(text) >= n else [text]

        query_ngrams = set(get_ngrams(query, 2) + get_ngrams(query, 3))

        # 计算每个文档的得分
        scored = []
        for doc in self._fallback_docs:
            doc_ngrams = set(get_ngrams(doc["text"], 2) + get_ngrams(doc["text"], 3))

            # Jaccard相似度
            if query_ngrams and doc_ngrams:
                intersection = len(query_ngrams & doc_ngrams)
                union = len(query_ngrams | doc_ngrams)
                score = intersection / union if union > 0 else 0
            else:
                score = 0

            # 额外关键词加权
            keywords = ["碳排放", "配额", "碳交易", "物流", "运输", "排放因子",
                       "碳市场", "清缴", "核查", "报告", "罚款", "履约"]
            for kw in keywords:
                if kw in query and kw in doc["text"]:
                    score += 0.1

            scored.append((score, doc))

        # 排序取Top-K
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, doc in scored[:k]:
            results.append({
                "text": doc["text"],
                "metadata": doc.get("metadata", {}),
                "distance": 1 - score,  # 模拟distance（越小越相关）
            })
        return results

    def get_stats(self) -> dict:
        """获取知识库统计信息"""
        if CHROMA_AVAILABLE:
            return {
                "total_chunks": self.collection.count(),
                "collection_name": self.collection_name,
                "mode": "chromadb",
            }
        else:
            return {
                "total_chunks": len(self._fallback_docs),
                "collection_name": self.collection_name,
                "mode": "tfidf_fallback",
            }

    def clear(self):
        """清空知识库"""
        if CHROMA_AVAILABLE:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "中国碳交易政策法规知识库"},
            )
        else:
            self._fallback_docs = []
            cache_file = Path(self.persist_dir) / "fallback_docs.json"
            if cache_file.exists():
                cache_file.unlink()
        print("✅ 知识库已清空")
