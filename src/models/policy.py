"""政策问答数据模型"""
from pydantic import BaseModel, Field
from typing import Optional


class PolicyQuestion(BaseModel):
    """政策问答输入"""
    question: str = Field(..., description="用户自然语言问题")
    carbon_profile: dict = Field(default_factory=dict, description="企业碳画像数据")


class RetrievedSource(BaseModel):
    """检索到的政策来源"""
    source: str = Field(..., description="来源文件名")
    date: str = Field("", description="发布日期")
    relevance: Optional[float] = Field(None, description="相关度")


class PolicyAnswer(BaseModel):
    """政策问答输出"""
    question: str
    retrieved_sources: list[RetrievedSource]
    answer: str
