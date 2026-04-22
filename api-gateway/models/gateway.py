"""
Gateway 管理相关的请求/响应模型（App & Key）
"""
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


# ─── App 模型 ─────────────────────────────────────────────────
class AppCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=64, description="应用唯一名称（英文或中文）")
    description: str = Field("", description="应用描述")
    contact: str = Field("", description="联系人邮箱或姓名")
    scopes: str = Field(
        "query,chat,wiki",
        description="权限范围，逗号分隔。可选值：query / chat / wiki",
    )
    rate_limit: int = Field(60, ge=1, le=3000, description="每分钟最大请求次数")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "crm-system",
                "description": "CRM 系统集成，用于商机查询",
                "contact": "zhang@company.com",
                "scopes": "query,chat",
                "rate_limit": 120,
            }
        }
    }


class AppUpdate(BaseModel):
    description: Optional[str] = None
    contact: Optional[str] = None
    scopes: Optional[str] = None
    rate_limit: Optional[int] = Field(None, ge=1, le=3000)
    is_active: Optional[bool] = None


class AppOut(BaseModel):
    id: int
    name: str
    description: str
    contact: str
    scopes: str
    rate_limit: int
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}


# ─── API Key 模型 ─────────────────────────────────────────────
class KeyCreate(BaseModel):
    label: str = Field("default", max_length=64, description="密钥标签，便于区分用途")


class KeyOut(BaseModel):
    id: int
    app_id: int
    label: str
    key_prefix: str
    is_active: bool
    last_used_at: Optional[str]
    created_at: str

    model_config = {"from_attributes": True}


class KeyCreated(KeyOut):
    """仅在创建时返回，包含完整明文 Key（之后无法再次获取）"""
    api_key: str = Field(..., description="完整 API Key，请妥善保存，仅显示一次")


# ─── 日志模型 ─────────────────────────────────────────────────
class LogOut(BaseModel):
    id: int
    app_id: Optional[int]
    app_name: Optional[str]
    endpoint: Optional[str]
    method: Optional[str]
    status_code: Optional[int]
    latency_ms: Optional[int]
    created_at: str
