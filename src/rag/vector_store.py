"""ChromaDB向量知识库管理"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
from pathlib import Path
from src.config import CHROMA_DB_DIR, EMBEDDING_MODEL


class PolicyVectorStore:
    """碳交易政策向量知识库"""

    def __init__(self, persist_dir: str = None):
        """
        初始化向量数据库

        Args:
            persist_dir: ChromaDB持久化目录，默认使用配置中的路径
        """
        persist_dir = persist_dir or str(CHROMA_DB_DIR)
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection_name = "carbon_policy"

        try:
            self.collection = self.client.get_collection(self.collection_name)
            print(f"✅ 已加载已有知识库: {self.collection.count()} 个文档块")
        except Exception:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "中国碳交易政策法规知识库"},
            )
            print("✅ 已创建新知识库")

    def add_documents(self, chunks: List[Dict], doc_source: str, doc_date: str = ""):
        """
        向知识库添加文档chunk

        Args:
            chunks: [{"text": "...", "metadata": {...}}, ...]
            doc_source: 文档来源
            doc_date: 文档发布日期
        """
        if not chunks:
            return

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

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        print(f"✅ 已入库 {len(chunks)} 个文档块 来自: {doc_source}")

    def search(self, query: str, k: int = 5) -> List[Dict]:
        """
        语义检索最相关的政策条款

        Args:
            query: 用户自然语言问题
            k: 返回结果数量

        Returns:
            List[Dict]: [{"text": "...", "metadata": {...}, "distance": 0.xx}, ...]
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=k,
        )

        formatted = []
        if results["documents"] and results["documents"][0]:
            for i in range(len(results["documents"][0])):
                formatted.append({
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else None,
                })
        return formatted

    def get_stats(self) -> dict:
        """获取知识库统计信息"""
        return {
            "total_chunks": self.collection.count(),
            "collection_name": self.collection_name,
        }

    def clear(self):
        """清空知识库（重新入库时使用）"""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"description": "中国碳交易政策法规知识库"},
        )
        print("✅ 知识库已清空")
