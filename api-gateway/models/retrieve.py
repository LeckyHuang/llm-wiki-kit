"""
Retrieve 相关的请求/响应模型（纯检索，不调用 LLM 生成总结）
"""
from typing import Optional
from pydantic import BaseModel, Field


class RetrieveRequest(BaseModel):
    """知识库检索请求"""
    query: str = Field(..., min_length=1, description="检索query，支持自然语言或关键词")
    entity_type: Optional[str] = Field(
        None,
        description="按实体类型（子目录名）精确过滤，如 cases、products、docs 等",
    )
    status: Optional[str] = Field(
        "active",
        description="生命周期过滤：active、outdated、archived，默认只返回 active",
    )
    tags: Optional[list[str]] = Field(
        None,
        description="按标签过滤，多个标签为 AND 关系",
    )
    query_mode: str = Field(
        "keyword",
        description="查询模式：keyword=纯关键词分词（默认）、nlp=LLM解析意图后检索",
    )
    limit: int = Field(10, ge=1, le=50, description="返回条数上限")
    rerank: bool = Field(
        False,
        description="是否用 LLM 对结果做相关性重排（会额外消耗 token）",
    )
    max_chars_per_result: int = Field(
        2000,
        ge=100,
        le=10000,
        description="每条结果的正文截断长度",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "智慧展厅 多媒体互动",
                "entity_type": "cases",
                "status": "active",
                "limit": 5,
                "rerank": True,
            }
        }
    }


class RetrieveResult(BaseModel):
    """单条检索结果"""
    title: str = Field(..., description="实体标题（来自 frontmatter.title 或文件名）")
    entity_type: str = Field(..., description="实体类型（所属子目录名）")
    source: str = Field(..., description="文件相对路径，如 cases/xxx.md")
    relevance_score: float = Field(
        ..., ge=0.0, le=1.0, description="相关性得分"
    )
    frontmatter: dict = Field(default_factory=dict, description="完整 frontmatter 元数据")
    content: str = Field(
        ..., description="正文内容（已按 max_chars_per_result 截断）"
    )


class RetrieveResponse(BaseModel):
    """检索响应"""
    results: list[RetrieveResult] = Field(..., description="检索结果列表")
    total: int = Field(..., description="符合条件的总条数（未截断前）")
    query: str = Field(..., description="原始 query")
    reranked: bool = Field(..., description="是否经过 LLM 重排")
    chars_used: int = Field(..., description="本次检索加载的总字符数")
