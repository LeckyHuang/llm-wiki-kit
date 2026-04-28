"""
Ingest 相关的请求/响应模型
"""
from typing import Optional
from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    """Ingest 任务响应"""
    task_id: str = Field(..., description="任务唯一标识")
    status: str = Field(..., description="任务状态：committed / pending_review / failed")
    entity_path: Optional[str] = Field(None, description="入库后的实体路径（仅 committed 状态）")
    preview: Optional[dict] = Field(None, description="提取结果预览（仅 pending_review 状态）")
    message: Optional[str] = Field(None, description="状态说明或错误信息")

    model_config = {
        "json_schema_extra": {
            "example": {
                "task_id": "ing_abc123",
                "status": "pending_review",
                "preview": {
                    "title": "某项目案例",
                    "type": "case",
                    "summary": "一句话摘要",
                },
            }
        }
    }


class IngestCommitRequest(BaseModel):
    """手动确认入库请求"""
    task_id: str = Field(..., description="待确认的任务 ID")
    conflict_resolutions: dict[str, str] = Field(
        default_factory=dict,
        description="冲突裁决：{conflict_id: 'new'|'old'}",
    )
    approved_suggestions: list[str] = Field(
        default_factory=list,
        description="用户勾选的 schema 建议字段名列表",
    )


class IngestTaskStatus(BaseModel):
    """Ingest 任务状态查询响应"""
    task_id: str
    status: str
    created_at: str
    updated_at: str
    preview: Optional[dict] = None
    entity_path: Optional[str] = None
    error: Optional[str] = None
