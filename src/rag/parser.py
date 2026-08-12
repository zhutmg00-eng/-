"""政策文档解析器

支持格式：PDF, DOCX, HTML
功能：解析 → 清洗 → 切分chunk
"""
from typing import List, Dict
from pathlib import Path
import fitz  # PyMuPDF
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
from bs4 import BeautifulSoup
import re


def parse_pdf(file_path: Path) -> str:
    """解析PDF文档为纯文本"""
    doc = fitz.open(file_path)
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)


def parse_docx(file_path: Path) -> str:
    """解析Word文档为纯文本"""
    if not DOCX_AVAILABLE:
        print(f"⚠️ python-docx未安装，无法解析: {file_path.name}")
        return ""
    doc = Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])


def parse_html(file_path: Path) -> str:
    """解析HTML文档为纯文本"""
    soup = BeautifulSoup(file_path.read_text(encoding="utf-8"), "html.parser")
    # 移除script和style标签
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    return soup.get_text(separator="\n")


def parse_document(file_path: Path) -> str:
    """根据文件扩展名自动选择解析器"""
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        return parse_pdf(file_path)
    elif ext in (".docx", ".doc"):
        return parse_docx(file_path)
    elif ext in (".html", ".htm"):
        return parse_html(file_path)
    elif ext == ".txt":
        return file_path.read_text(encoding="utf-8")
    else:
        print(f"⚠️ 不支持的文件格式: {ext} ({file_path.name})")
        return ""


def clean_policy_text(raw_text: str) -> str:
    """
    清洗政策文档文本
    - 移除多余空行
    - 合并断行（政策文档常有页码导致的断行）
    - 保留章节标题结构
    """
    lines = raw_text.split("\n")
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 简单合并：如果上一行不是标题（以数字+句号或"第"开头）
        if cleaned and not (
            line.startswith(("第", "一、", "二、", "三、", "1.", "2.", "3."))
            or len(line) < 30  # 短行可能是标题
        ):
            cleaned[-1] += line
        else:
            cleaned.append(line)
    return "\n".join(cleaned)


def chunk_policy_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 150,
    doc_source: str = "",
    doc_date: str = "",
) -> List[Dict]:
    """
    将政策文档切分为可检索的chunk

    策略：
    - 以自然段落分割
    - 每个chunk约800字符（中文约400字），overlap 150字符
    - 每个chunk保留元数据

    Args:
        text: 清洗后的政策全文
        chunk_size: 每个chunk的最大字符数
        overlap: 相邻chunk的重叠字符数
        doc_source: 来源文档名
        doc_date: 文档发布日期

    Returns:
        List[Dict]: [{"text": "...", "metadata": {...}}, ...]
    """
    paragraphs = text.split("\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) > chunk_size:
            if current_chunk:
                chunks.append({
                    "text": current_chunk.strip(),
                    "metadata": {
                        "source": doc_source,
                        "date": doc_date,
                    },
                })
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = overlap_text + "\n" + para
            else:
                current_chunk = para
        else:
            current_chunk += "\n" + para if current_chunk else para

    if current_chunk.strip():
        chunks.append({
            "text": current_chunk.strip(),
            "metadata": {
                "source": doc_source,
                "date": doc_date,
            },
        })

    return chunks


def process_document(file_path: Path, doc_date: str = "") -> List[Dict]:
    """
    完整处理流程：解析 → 清洗 → 切分

    Args:
        file_path: 文档文件路径
        doc_date: 文档发布日期

    Returns:
        List[Dict]: chunk列表
    """
    raw_text = parse_document(file_path)
    if not raw_text.strip():
        return []

    cleaned_text = clean_policy_text(raw_text)
    chunks = chunk_policy_text(
        cleaned_text,
        doc_source=file_path.name,
        doc_date=doc_date,
    )
    print(f"📄 {file_path.name}: {len(chunks)} 个chunk")
    return chunks
