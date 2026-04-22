"""
认证与限流
- API Key 认证：X-API-Key header，SHA-256 哈希校验
- 管理员认证：X-Admin-Key header，对比 GATEWAY_ADMIN_KEY
- 滑动窗口限流：每个 App 独立计数（内存，重启清零）
"""
import hashlib
import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import Header, HTTPException, Request  # noqa: F401

from config import DEFAULT_RATE_LIMIT, GATEWAY_ADMIN_KEY
from db import get_conn

# ─── 限流：滑动窗口（1 分钟） ────────────────────────────────
_rate_windows: dict[int, deque] = defaultdict(deque)
_WINDOW_SECONDS = 60


def _check_rate_limit(app_id: int, limit: int) -> None:
    now = time.time()
    win = _rate_windows[app_id]
    while win and win[0] < now - _WINDOW_SECONDS:
        win.popleft()
    if len(win) >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"请求过于频繁，当前应用限额 {limit} 次/分钟，请稍后重试",
            headers={"Retry-After": "60"},
        )
    win.append(now)


# ─── API Key 哈希工具 ─────────────────────────────────────────
def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


# ─── 认证上下文 ───────────────────────────────────────────────
class AppContext:
    __slots__ = ("app_id", "app_name", "key_id", "scopes", "rate_limit")

    def __init__(self, app_id: int, app_name: str, key_id: int, scopes: str, rate_limit: int):
        self.app_id = app_id
        self.app_name = app_name
        self.key_id = key_id
        self.scopes = set(scopes.split(","))
        self.rate_limit = rate_limit

    def require_scope(self, scope: str) -> None:
        if scope not in self.scopes:
            raise HTTPException(status_code=403, detail=f"当前应用无 '{scope}' 权限")


# ─── FastAPI 依赖：API Key 校验 ───────────────────────────────
async def get_app_context(request: Request, x_api_key: Optional[str] = Header(None)) -> AppContext:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="缺少 X-API-Key 请求头")

    key_hashed = hash_key(x_api_key)
    conn = get_conn()
    row = conn.execute(
        """
        SELECT k.id AS key_id, k.app_id, k.is_active AS key_active,
               a.name AS app_name, a.scopes, a.rate_limit, a.is_active AS app_active
        FROM api_keys k
        JOIN apps a ON a.id = k.app_id
        WHERE k.key_hash = ?
        """,
        (key_hashed,),
    ).fetchone()

    if row:
        # 异步更新 last_used_at（不阻塞主流程）
        conn.execute(
            "UPDATE api_keys SET last_used_at = datetime('now','localtime') WHERE id = ?",
            (row["key_id"],),
        )
        conn.commit()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="无效的 API Key")
    if not row["app_active"]:
        raise HTTPException(status_code=403, detail="该应用已被停用")
    if not row["key_active"]:
        raise HTTPException(status_code=403, detail="该 API Key 已被吊销")

    ctx = AppContext(
        app_id=row["app_id"],
        app_name=row["app_name"],
        key_id=row["key_id"],
        scopes=row["scopes"],
        rate_limit=row["rate_limit"],
    )
    _check_rate_limit(ctx.app_id, ctx.rate_limit)

    # 写入 request.state，供日志中间件读取
    request.state.app_id = ctx.app_id
    request.state.key_id = ctx.key_id
    request.state.app_name = ctx.app_name
    return ctx


# ─── FastAPI 依赖：管理员认证 ─────────────────────────────────
async def require_admin(x_admin_key: Optional[str] = Header(None)) -> None:
    if not x_admin_key or x_admin_key != GATEWAY_ADMIN_KEY:
        raise HTTPException(status_code=401, detail="管理员密钥无效")
