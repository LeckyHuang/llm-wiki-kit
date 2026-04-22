"""
查询相关的请求/响应模型
"""
from typing import Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """结构化知识查询请求"""
    industry: Optional[str] = Field(None, description="目标行业（如：通信、金融、医疗），留空表示不限")
    hall_type: Optional[str] = Field(None, description="展厅类型，留空表示不限")
    project_type: Optional[str] = Field(None, description="项目类型：新建 / 改造升级 / 咨询规划 / 运营维护")
    include_competitors: bool = Field(False, description="是否加载竞品参考内容")
    include_policies: bool = Field(False, description="是否加载政策依据内容")
    include_credentials: bool = Field(False, description="是否加载资质与案例内容")
    question: Optional[str] = Field(None, description="补充问题或说明（附加到查询末尾）")
    custom_prompt: Optional[str] = Field(None, description="自定义查询指令（覆盖默认提示词模板）")

    model_config = {
        "json_schema_extra": {
            "example": {
                "industry": "通信",
                "hall_type": "企业展厅",
                "project_type": "新建",
                "include_competitors": True,
                "include_policies": False,
                "include_credentials": False,
                "question": "重点关注沉浸式体验模块",
            }
        }
    }


class ChatRequest(BaseModel):
    """自由问答请求"""
    message: str = Field(..., min_length=1, description="用户问题")

    model_config = {
        "json_schema_extra": {
            "example": {"message": "我们的展厅方案在政务行业有哪些成功案例？"}
        }
    }


class QueryResponse(BaseModel):
    """统一查询响应"""
    result: str = Field(..., description="LLM 生成的知识摘要")
    wiki_chars_used: int = Field(..., description="本次加载的知识库字符数")
    provider: str = Field(..., description="使用的 LLM 提供商")
