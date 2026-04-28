"""
Ingest 路由：POST /v1/ingest  /  GET /v1/ingest/{task_id}
双工模式：
- auto_commit=true：全自动，提取后直接写入 wiki/
- auto_commit=false：半自动，提取后保存到 wiki/.pending/ 等待人工校对
"""
import json
import logging
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.exceptions import HTTPException

from auth import AppContext, get_app_context
from config import SCHEMA_DIR, WIKI_PATH
from llm_client import _get_client
from models.ingest import IngestCommitRequest, IngestResponse, IngestTaskStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["知识库摄入"])

# ─── 复用 wiki-app-hub 的 ingest_engine（已做 pdfplumber 兼容）────
_INGEST_ENGINE_DIR = Path(__file__).resolve().parent.parent.parent / "wiki-app-hub"
if str(_INGEST_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(_INGEST_ENGINE_DIR))

try:
    import ingest_engine as _ingest_engine
except Exception as e:
    logger.error(f"无法加载 ingest_engine: {e}")
    _ingest_engine = None

# ─── 路径常量 ─────────────────────────────────────────────────
_PENDING_DIR = WIKI_PATH / ".pending"
_TEMP_DIR = Path(__file__).resolve().parent.parent / "temp_uploads"
_SCHEMA_DIR = SCHEMA_DIR  # 从 config 读取，指向 llm-wiki-kit/schema/


# ─── 辅助函数 ─────────────────────────────────────────────────
def _gen_task_id() -> str:
    return f"ing_{uuid.uuid4().hex[:12]}"


def _save_pending(task_id: str, result: dict, filename: str) -> Path:
    _PENDING_DIR.mkdir(parents=True, exist_ok=True)
    pending_file = _PENDING_DIR / f"{task_id}.json"
    record = {
        "task_id": task_id,
        "status": "pending_review",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "filename": filename,
        "result": result,
    }
    pending_file.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return pending_file


def _load_pending(task_id: str) -> Optional[dict]:
    pending_file = _PENDING_DIR / f"{task_id}.json"
    if not pending_file.exists():
        return None
    try:
        return json.loads(pending_file.read_text(encoding="utf-8"))
    except Exception:
        return None


def _remove_pending(task_id: str) -> None:
    pending_file = _PENDING_DIR / f"{task_id}.json"
    if pending_file.exists():
        pending_file.unlink()


def _sync_call_llm(system_prompt: str, user_prompt: str) -> str:
    """同步调用 LLM，返回完整文本。"""
    try:
        client, model = _get_client()
    except Exception as e:
        raise RuntimeError(f"LLM 客户端初始化失败：{e}")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=4000,
            stream=False,
        )
        return response.choices[0].message.content
    except Exception as e:
        raise RuntimeError(f"LLM 调用失败：{e}")


# ─── 主路由：创建 Ingest 任务 ─────────────────────────────────
@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="摄入文件到知识库",
    description=(
        "上传文件（PDF/PPTX/DOCX/TXT/MD），经 LLM 提取后入库。\n\n"
        "- `auto_commit=true`：全自动，提取后直接写入 wiki/（适合批量处理）\n"
        "- `auto_commit=false`（默认）：半自动，提取后进入 pending_review 状态，"
        "  需人工在 wiki-app-hub 界面校对后确认入库\n\n"
        "**所需权限**：`query`（摄入本质上是写操作，暂用 query scope，可后续拆分为独立 scope）"
    ),
)
async def create_ingest(
    auto_commit: bool = Form(False, description="是否自动确认入库"),
    file: UploadFile = File(..., description="待摄入文件"),
    ctx: AppContext = Depends(get_app_context),
) -> IngestResponse:
    ctx.require_scope("query")

    if _ingest_engine is None:
        raise HTTPException(status_code=503, detail="Ingest 引擎未加载，请检查依赖")

    task_id = _gen_task_id()
    _TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 保存上传文件
    temp_path = _TEMP_DIR / f"{task_id}_{file.filename}"
    try:
        with temp_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        logger.exception("保存上传文件失败")
        raise HTTPException(status_code=500, detail=f"文件保存失败：{e}")
    finally:
        file.file.close()

    try:
        # 2. 提取文本
        extracted_text = _ingest_engine.extract_text(temp_path)

        # 3. 读取领域配置和现有实体
        domain_config = _ingest_engine.load_domain_config(_SCHEMA_DIR)
        existing_entities = _ingest_engine.scan_existing_entities(WIKI_PATH)

        # schema-core.md 可选
        schema_core = ""
        schema_core_path = _SCHEMA_DIR / "SCHEMA-CORE.md"
        if schema_core_path.exists():
            schema_core = schema_core_path.read_text(encoding="utf-8")

        # 4. 构建 prompt 并调用 LLM
        system_prompt, user_prompt = _ingest_engine.build_ingest_prompt(
            filename=file.filename,
            extracted_text=extracted_text,
            domain_config=domain_config,
            existing_entities=existing_entities,
            schema_core=schema_core,
        )
        raw_output = _sync_call_llm(system_prompt, user_prompt)

        # 5. 解析结果
        result = _ingest_engine.parse_llm_output(raw_output)

        # 6. 处理结果
        if auto_commit:
            # 全自动：直接 commit
            commit_result = _ingest_engine.commit_ingest(
                result=result,
                wiki_path_root=WIKI_PATH,
                conflict_resolutions={},
                approved_suggestions=[],
            )
            # 清理临时文件
            temp_path.unlink(missing_ok=True)
            return IngestResponse(
                task_id=task_id,
                status="committed",
                entity_path=result.get("wiki_path"),
                preview={
                    "title": result.get("title", ""),
                    "type": result["frontmatter"].get("type", ""),
                    "summary": result.get("summary", ""),
                    "written": commit_result.get("written", []),
                },
            )
        else:
            # 半自动：保存到 pending
            _save_pending(task_id, result, file.filename)
            # 保留临时文件供后续校对时参考（可选）
            return IngestResponse(
                task_id=task_id,
                status="pending_review",
                preview={
                    "title": result.get("title", ""),
                    "type": result["frontmatter"].get("type", ""),
                    "summary": result.get("summary", ""),
                    "wiki_path": result.get("wiki_path", ""),
                    "conflicts_count": len(result.get("conflicts", [])),
                    "suggestions_count": len(result.get("schema_suggestions", [])),
                },
            )

    except HTTPException:
        temp_path.unlink(missing_ok=True)
        raise
    except Exception as e:
        logger.exception("Ingest 处理失败")
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Ingest 处理失败：{e}")


# ─── 查询任务状态 ─────────────────────────────────────────────
@router.get(
    "/ingest/{task_id}",
    response_model=IngestTaskStatus,
    summary="查询 Ingest 任务状态",
)
async def get_ingest_status(
    task_id: str,
    ctx: AppContext = Depends(get_app_context),
) -> IngestTaskStatus:
    ctx.require_scope("query")

    record = _load_pending(task_id)
    if record:
        return IngestTaskStatus(
            task_id=record["task_id"],
            status=record["status"],
            created_at=record["created_at"],
            updated_at=record["updated_at"],
            preview=record.get("result"),
        )

    # 如果不在 pending 中，可能是已 commit 的（简化处理：通过扫描 wiki 确认）
    # 实际生产环境可用 SQLite 任务表追踪
    raise HTTPException(status_code=404, detail="任务不存在或已过期")


# ─── 手动确认入库（供 wiki-app-hub 调用或外部系统回调）────────
@router.post(
    "/ingest/{task_id}/commit",
    response_model=IngestResponse,
    summary="确认 pending 任务入库",
    description="对处于 pending_review 状态的 Ingest 任务执行确认入库。",
)
async def commit_pending_ingest(
    task_id: str,
    req: IngestCommitRequest,
    ctx: AppContext = Depends(get_app_context),
) -> IngestResponse:
    ctx.require_scope("query")

    if _ingest_engine is None:
        raise HTTPException(status_code=503, detail="Ingest 引擎未加载")

    record = _load_pending(task_id)
    if not record:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")

    if record["status"] != "pending_review":
        raise HTTPException(status_code=400, detail=f"任务状态为 {record['status']}，无法确认入库")

    result = record["result"]

    try:
        commit_result = _ingest_engine.commit_ingest(
            result=result,
            wiki_path_root=WIKI_PATH,
            conflict_resolutions=req.conflict_resolutions,
            approved_suggestions=req.approved_suggestions,
        )

        # 标记为已提交并清理 pending
        record["status"] = "committed"
        record["updated_at"] = datetime.now().isoformat()
        record["entity_path"] = result.get("wiki_path")

        pending_file = _PENDING_DIR / f"{task_id}.json"
        pending_file.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

        # 可选：清理临时上传文件
        temp_path = _TEMP_DIR / f"{task_id}_{record['filename']}"
        temp_path.unlink(missing_ok=True)

        return IngestResponse(
            task_id=task_id,
            status="committed",
            entity_path=result.get("wiki_path"),
            preview={
                "title": result.get("title", ""),
                "type": result["frontmatter"].get("type", ""),
                "written": commit_result.get("written", []),
            },
        )

    except Exception as e:
        logger.exception("确认入库失败")
        raise HTTPException(status_code=500, detail=f"确认入库失败：{e}")


# ─── 列出 pending 任务（供 wiki-app-hub 拉取）─────────────────
@router.get(
    "/ingest/pending/list",
    summary="列出所有待校对的 Ingest 任务",
    response_model=list[IngestTaskStatus],
)
async def list_pending_ingests(
    ctx: AppContext = Depends(get_app_context),
) -> list[IngestTaskStatus]:
    ctx.require_scope("query")

    if not _PENDING_DIR.exists():
        return []

    results: list[IngestTaskStatus] = []
    for pf in sorted(_PENDING_DIR.glob("ing_*.json")):
        try:
            record = json.loads(pf.read_text(encoding="utf-8"))
            if record.get("status") == "pending_review":
                results.append(
                    IngestTaskStatus(
                        task_id=record["task_id"],
                        status=record["status"],
                        created_at=record["created_at"],
                        updated_at=record["updated_at"],
                        preview=record.get("result"),
                    )
                )
        except Exception:
            continue

    return results
