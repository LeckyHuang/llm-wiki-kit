"""
Wiki API Gateway
将 llm-wiki-kit 的核心知识库能力封装为对外 REST API。

启动：uvicorn main:app --host 0.0.0.0 --port 8001 --reload
文档：http://localhost:8001/docs
"""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import WIKI_PATH
from db import get_conn, init_db
from llm_client import health_check as llm_health
from routers import gateway as gateway_router
from routers import query as query_router
from routers import wiki as wiki_router
from wiki_reader import wiki_stats

import sys as _sys
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    stream=_sys.stdout,
    encoding="utf-8",
)
logger = logging.getLogger("api-gateway")


# ─── 生命周期 ─────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("[OK] Gateway DB initialized")
    logger.info(f"[Wiki] path={WIKI_PATH}  exists={WIKI_PATH.exists()}")
    stats = wiki_stats()
    logger.info(f"[Wiki] total entries={stats['total']}")
    yield
    logger.info("[Shutdown] API Gateway stopped")


# ─── FastAPI 应用 ─────────────────────────────────────────────
app = FastAPI(
    title="Wiki API Gateway",
    version="1.0.0",
    description="""
## Wiki 知识库 API Gateway

将 **llm-wiki-kit** 的核心知识库能力封装为标准 REST API，供外部系统调用。

### 认证方式

所有业务接口需在请求头中携带：
```
X-API-Key: wk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

管理接口（App/Key 管理、日志查询）需在请求头中携带：
```
X-Admin-Key: <管理员主密钥>
```

### 快速接入步骤

1. 使用管理员密钥调用 `POST /v1/apps` 注册你的应用
2. 调用 `POST /v1/apps/{app_id}/keys` 获取 API Key（**仅显示一次，请妥善保存**）
3. 使用 API Key 调用 `/v1/query` 或 `/v1/chat` 查询知识库

### 权限范围（Scopes）

| Scope | 说明 |
|-------|------|
| `query` | 结构化知识查询（POST /v1/query） |
| `chat` | 自由问答（POST /v1/chat） |
| `wiki` | 知识库元数据浏览（GET /v1/wiki/*） |
""",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "知识库查询", "description": "调用 LLM 对知识库进行查询"},
        {"name": "知识库信息", "description": "浏览知识库结构和元数据，不调用 LLM"},
        {"name": "Gateway 管理", "description": "管理注册应用和 API Key（需要管理员密钥）"},
    ],
)

# ─── CORS ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── 请求日志中间件（记录耗时 & 写入 gateway_logs） ───────────
@app.middleware("http")
async def log_requests(request: Request, call_next) -> Response:
    start = time.monotonic()
    response: Response = await call_next(request)
    latency_ms = int((time.monotonic() - start) * 1000)

    # 只记录 /v1/ 路径（排除健康检查和文档）
    path = request.url.path
    if path.startswith("/v1/"):
        # 从请求状态中提取 app 上下文（由 auth 依赖写入）
        app_id: int | None = getattr(request.state, "app_id", None)
        key_id: int | None = getattr(request.state, "key_id", None)
        app_name: str | None = getattr(request.state, "app_name", None)
        try:
            conn = get_conn()
            conn.execute(
                """INSERT INTO gateway_logs
                   (app_id, key_id, app_name, endpoint, method, status_code, latency_ms)
                   VALUES (?,?,?,?,?,?,?)""",
                (app_id, key_id, app_name, path, request.method,
                 response.status_code, latency_ms),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    logger.info(
        f"{request.method} {path} → {response.status_code} ({latency_ms}ms)"
    )
    return response


# ─── 全局异常处理 ─────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"未处理的异常：{request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请联系管理员"},
    )


# ─── 路由注册 ─────────────────────────────────────────────────
app.include_router(query_router.router)
app.include_router(wiki_router.router)
app.include_router(gateway_router.router)


# ─── 健康检查（公开，无需认证） ──────────────────────────────
@app.get("/health", tags=["系统"], summary="健康检查")
async def health():
    llm = await llm_health()
    stats = wiki_stats()
    return {
        "status": "ok",
        "wiki": {
            "path": str(WIKI_PATH),
            "exists": WIKI_PATH.exists(),
            "total_entries": stats["total"],
            "breakdown": stats["breakdown"],
        },
        "llm": llm,
    }


@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": "Wiki API Gateway",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
