"""
查询相关的请求/响应模型（领域无关通用版本）
"""
from typing import Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """结构化知识查询请求"""
    industry: Optional[str] = Field(
        None,
        description="行业 / 领域筛选（对应 wiki/industries/ 目录），留空表示不限",
    )
    hall_type: Optional[str] = Field(
        None,
        description="二级分类筛选（对应 wiki/hall-types/ 目录），留空表示不限",
    )
    project_type: Optional[str] = Field(
        None,
        description="项目阶段或类型（自由文本，传入 prompt 作为上下文参考）",
    )
    include_competitors: bool = Field(False, description="是否加载竞品参考内容（wiki/competitors/）")
    include_policies: bool = Field(False, description="是否加载政策依据内容（wiki/policies/）")
    include_credentials: bool = Field(False, description="是否加载资质与案例内容（wiki/credentials/）")
    question: Optional[str] = Field(None, description="补充问题或说明（附加到查询末尾）")
    custom_prompt: Optional[str] = Field(
        None,
        description="完全自定义的查询指令，设置后将跳过默认 prompt 模板直接使用",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "industry": "金融",
                "hall_type": "品牌旗舰店",
                "project_type": "新建",
                "include_competitors": True,
                "include_policies": False,
                "include_credentials": False,
                "question": "重点关注数字化互动体验部分",
            }
        }
    }


class ChatRequest(BaseModel):
    """自由问答请求"""
    message: str = Field(..., min_length=1, description="用户问题")

    model_config = {
        "json_schema_extra": {
            "example": {"message": "知识库中有哪些关于智慧零售的成功案例？"}
        }
    }


class QueryResponse(BaseModel):
    """统一查询响应"""
    result: str = Field(..., description="LLM 生成的知识摘要")
    wiki_chars_used: int = Field(..., description="本次加载的知识库字符数")
    provider: str = Field(..., description="使用的 LLM 提供商")
