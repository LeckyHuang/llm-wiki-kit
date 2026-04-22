"""
Gateway 管理路由（仅管理员可用，需要 X-Admin-Key）
- App CRUD：/v1/apps
- Key 管理：/v1/apps/{app_id}/keys
- 访问日志：/v1/gateway/logs
"""
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import hash_key, require_admin
from db import get_conn
from models.gateway import AppCreate, AppOut, AppUpdate, KeyCreate, KeyCreated, KeyOut, LogOut

router = APIRouter(tags=["Gateway 管理"])


# ─── App 管理 ─────────────────────────────────────────────────

@router.get(
    "/v1/apps",
    response_model=list[AppOut],
    summary="列出所有注册应用",
)
async def list_apps(_: None = Depends(require_admin)) -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM apps ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post(
    "/v1/apps",
    response_model=AppOut,
    status_code=201,
    summary="注册新应用",
    description="注册后需要再调用 `POST /v1/apps/{app_id}/keys` 为该应用创建 API Key。",
)
async def create_app(req: AppCreate, _: None = Depends(require_admin)) -> dict:
    valid_scopes = {"query", "chat", "wiki"}
    given = {s.strip() for s in req.scopes.split(",")}
    invalid = given - valid_scopes
    if invalid:
        raise HTTPException(status_code=400, detail=f"无效的 scope：{invalid}，可选值：{valid_scopes}")

    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO apps (name, description, contact, scopes, rate_limit) VALUES (?,?,?,?,?)",
            (req.name, req.description, req.contact, req.scopes, req.rate_limit),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM apps WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)
    except Exception:
        raise HTTPException(status_code=409, detail=f"应用名称 '{req.name}' 已存在")
    finally:
        conn.close()


@router.get(
    "/v1/apps/{app_id}",
    response_model=AppOut,
    summary="获取应用详情",
)
async def get_app(app_id: int, _: None = Depends(require_admin)) -> dict:
    conn = get_conn()
    row = conn.execute("SELECT * FROM apps WHERE id = ?", (app_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="应用不存在")
    return dict(row)


@router.patch(
    "/v1/apps/{app_id}",
    response_model=AppOut,
    summary="更新应用信息",
)
async def update_app(app_id: int, req: AppUpdate, _: None = Depends(require_admin)) -> dict:
    conn = get_conn()
    row = conn.execute("SELECT * FROM apps WHERE id = ?", (app_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="应用不存在")

    fields, values = [], []
    if req.description is not None:
        fields.append("description = ?"); values.append(req.description)
    if req.contact is not None:
        fields.append("contact = ?"); values.append(req.contact)
    if req.scopes is not None:
        fields.append("scopes = ?"); values.append(req.scopes)
    if req.rate_limit is not None:
        fields.append("rate_limit = ?"); values.append(req.rate_limit)
    if req.is_active is not None:
        fields.append("is_active = ?"); values.append(1 if req.is_active else 0)

    if fields:
        values.append(app_id)
        conn.execute(f"UPDATE apps SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()

    row = conn.execute("SELECT * FROM apps WHERE id = ?", (app_id,)).fetchone()
    conn.close()
    return dict(row)


@router.delete(
    "/v1/apps/{app_id}",
    status_code=204,
    summary="停用应用（软删除）",
    description="将应用标记为停用，其所有 API Key 同时失效。数据不会物理删除。",
)
async def deactivate_app(app_id: int, _: None = Depends(require_admin)) -> None:
    conn = get_conn()
    row = conn.execute("SELECT id FROM apps WHERE id = ?", (app_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="应用不存在")
    conn.execute("UPDATE apps SET is_active = 0 WHERE id = ?", (app_id,))
    conn.commit()
    conn.close()


# ─── Key 管理 ─────────────────────────────────────────────────

@router.get(
    "/v1/apps/{app_id}/keys",
    response_model=list[KeyOut],
    summary="列出应用的所有 API Key",
)
async def list_keys(app_id: int, _: None = Depends(require_admin)) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM api_keys WHERE app_id = ? ORDER BY created_at DESC",
        (app_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post(
    "/v1/apps/{app_id}/keys",
    response_model=KeyCreated,
    status_code=201,
    summary="为应用创建新 API Key",
    description="**明文 Key 仅在此处返回一次，请立即保存。**",
)
async def create_key(app_id: int, req: KeyCreate, _: None = Depends(require_admin)) -> dict:
    conn = get_conn()
    row = conn.execute("SELECT id FROM apps WHERE id = ? AND is_active = 1", (app_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="应用不存在或已停用")

    # 生成 Key：wk_live_ + 40 位随机 hex
    raw_key = "wk_live_" + secrets.token_hex(20)
    key_prefix = raw_key[:16] + "..."        # 显示前缀，供用户识别
    key_hashed = hash_key(raw_key)

    cur = conn.execute(
        "INSERT INTO api_keys (app_id, label, key_hash, key_prefix) VALUES (?,?,?,?)",
        (app_id, req.label, key_hashed, key_prefix),
    )
    conn.commit()
    key_id = cur.lastrowid
    key_row = conn.execute("SELECT * FROM api_keys WHERE id = ?", (key_id,)).fetchone()
    conn.close()

    result = dict(key_row)
    result["api_key"] = raw_key    # 仅此一次返回明文
    return result


@router.delete(
    "/v1/apps/{app_id}/keys/{key_id}",
    status_code=204,
    summary="吊销 API Key",
)
async def revoke_key(app_id: int, key_id: int, _: None = Depends(require_admin)) -> None:
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM api_keys WHERE id = ? AND app_id = ?", (key_id, app_id)
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Key 不存在")
    conn.execute("UPDATE api_keys SET is_active = 0 WHERE id = ?", (key_id,))
    conn.commit()
    conn.close()


# ─── 访问日志 ─────────────────────────────────────────────────

@router.get(
    "/v1/gateway/logs",
    response_model=list[LogOut],
    summary="查看访问日志",
)
async def get_logs(
    app_id: Optional[int] = Query(None, description="按应用 ID 过滤"),
    date_from: Optional[str] = Query(None, description="起始日期，如 2025-01-01"),
    date_to: Optional[str] = Query(None, description="结束日期，如 2025-12-31"),
    limit: int = Query(100, ge=1, le=1000),
    _: None = Depends(require_admin),
) -> list[dict]:
    sql = "SELECT * FROM gateway_logs WHERE 1=1"
    params: list = []
    if app_id:
        sql += " AND app_id = ?"
        params.append(app_id)
    if date_from:
        sql += " AND created_at >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND created_at <= ?"
        params.append(date_to + " 23:59:59")
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    conn = get_conn()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]
