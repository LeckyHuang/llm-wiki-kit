import json
import logging
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import frontmatter as _frontmatter

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from openai import OpenAI
import bcrypt as _bcrypt
from pydantic import BaseModel

from db import get_db_connection, init_db

logger = logging.getLogger(__name__)
load_dotenv()

# ─── JWT / 认证配置 ──────────────────────────────────────────

SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    try:
        with open(".env", "a", encoding="utf-8") as f:
            f.write(f"\nSECRET_KEY={SECRET_KEY}\n")
        logger.info("已自动生成 SECRET_KEY 并追加到 .env 文件")
    except Exception:
        logger.warning("SECRET_KEY 未设置，重启后所有用户需重新登录，请在 .env 中设置 SECRET_KEY")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8

security = HTTPBearer()


def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return _bcrypt.checkpw(password.encode(), hashed.encode())

# ─── 路径配置 ────────────────────────────────────────────────

WIKI_PATH = Path(os.getenv("WIKI_PATH", "./wiki")).expanduser()
SOURCE_FILES_DIR = Path(os.getenv("SOURCE_FILES_DIR", "./source-files")).expanduser()
ESTIMATION_FILES_DIR = Path(os.getenv("ESTIMATION_FILES_DIR", "./estimation-files"))
PROMPTS_DIR = Path(os.getenv("PROMPTS_DIR", "./prompts"))
MAX_WIKI_CHARS = int(os.getenv("MAX_WIKI_CHARS", "80000"))
MAX_CHAT_WIKI_CHARS = int(os.getenv("MAX_CHAT_WIKI_CHARS", "40000"))

# ─── LLM 配置 ────────────────────────────────────────────────

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "moonshot")

PROVIDERS = {
    "moonshot": {
        "api_key_env": "MOONSHOT_API_KEY",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-128k",
    },
    "qwen": {
        "api_key_env": "QWEN_API_KEY",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-long",
    },
}


def get_llm_client():
    cfg = PROVIDERS.get(LLM_PROVIDER, PROVIDERS["moonshot"])
    return (
        OpenAI(api_key=os.getenv(cfg["api_key_env"]), base_url=cfg["base_url"]),
        cfg["model"],
    )


# ─── FastAPI 应用 ────────────────────────────────────────────

app = FastAPI(title="展厅方案知识库")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    ESTIMATION_FILES_DIR.mkdir(parents=True, exist_ok=True)
    admin_hash = hash_password("Lecky888")
    init_db(admin_hash)


# ─── Auth 工具函数 ────────────────────────────────────────────

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("user_id") is None:
            raise HTTPException(status_code=401, detail="无效的认证信息")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token 无效或已过期，请重新登录")


def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


# ─── Prompt 模板 ─────────────────────────────────────────────

DEFAULT_QUERY_PROMPT = """请为以下展厅方案需求提供知识库素材摘要：

- 行业：{industry}
- 展厅类型：{hall_type}
- 项目类型：{project_type}
- 需要内容：{needs_str}
{extra_question_line}
请从知识库中提取最相关内容，按以下结构输出：

## 相关历史案例
（3-5个，每个包含：项目名称、核心亮点、可借鉴之处）

## 推荐功能模块
（列出适合本项目的模块及简要说明）

## 方案框架
（从过往同类项目中提炼出通用方案结构骨架，包括：核心章节、内容要点、逻辑顺序建议）

## 政策与依据
（可引用的政策文件或行业标准，如无则省略此项）

## 竞品参考
（友商在同类项目的策略，如无则省略此项）

## 方案建议
（基于以上内容，给出2-3条核心建议）"""

PROMPT_VARIABLES = [
    'industry        — 所选行业，未选时为"不限"',
    'hall_type       — 展厅类型，未选时为"不限"',
    'project_type    — 项目类型，未选时为"不限"',
    'needs_str       — 勾选内容（竞品/政策/资质），未勾选时为"历史案例、功能模块"',
    "extra_question_line — 补充说明行（含换行），无补充说明时为空字符串",
]


def load_query_prompt() -> str:
    prompt_file = PROMPTS_DIR / "query_prompt.md"
    if prompt_file.exists():
        try:
            return prompt_file.read_text(encoding="utf-8")
        except Exception:
            pass
    return DEFAULT_QUERY_PROMPT


# ─── 源文件管理 ──────────────────────────────────────────────

_FILE_PRIORITY = {".pptx": 0, ".ppt": 1, ".pdf": 2}


def list_source_files() -> dict[str, dict]:
    """返回 {stem: {filename, ext, has_pdf}} 映射，下载优先取 PPT"""
    if not SOURCE_FILES_DIR.exists():
        return {}
    stem_files: dict[str, list] = {}
    for f in SOURCE_FILES_DIR.iterdir():
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        if ext not in _FILE_PRIORITY:
            continue
        stem_files.setdefault(f.stem, []).append(f.name)

    result = {}
    for stem, fnames in stem_files.items():
        best = min(fnames, key=lambda n: _FILE_PRIORITY.get(Path(n).suffix.lower(), 99))
        has_pdf = any(Path(n).suffix.lower() == ".pdf" for n in fnames)
        result[stem] = {
            "filename": best,
            "ext": Path(best).suffix.lower().lstrip("."),
            "has_pdf": has_pdf,
        }
    return result


# ─── Wiki 加载 ───────────────────────────────────────────────

ALWAYS_LOAD = ["modules", "proposal-stages"]

_OUTDATED_PREFIX = "⚠️ [此内容可能已过期，请核实后使用]\n\n"


def _read_wiki_file(md_file: Path) -> str | None:
    """读取 wiki 文件并应用生命周期过滤。archived 返回 None，outdated 加警示前缀。"""
    raw = md_file.read_text(encoding="utf-8").strip()
    if not raw:
        return None
    try:
        post = _frontmatter.loads(raw)
        status = str(post.metadata.get("status", "active")).lower()
        if status == "archived":
            return None
        content = raw
        if status == "outdated":
            content = _OUTDATED_PREFIX + raw
        return content
    except Exception:
        return raw


def load_directory(dir_path: Path) -> list[str]:
    chunks = []
    if not dir_path.exists():
        return chunks
    for md_file in sorted(dir_path.glob("**/*.md")):
        try:
            text = _read_wiki_file(md_file)
            if text:
                chunks.append(f"### 【{md_file.stem}】\n{text}")
        except Exception:
            pass
    return chunks


def load_single_md(file_path: Path) -> list[str]:
    if not file_path.exists():
        return []
    try:
        text = _read_wiki_file(file_path)
        if text:
            return [f"### 【{file_path.stem}】\n{text}"]
    except Exception:
        pass
    return []


def scan_wiki_dir(subdir: str, exclude_stems: set = None) -> list[str]:
    """扫描 wiki 子目录，返回实际存在的 .md 文件名（不含扩展名）"""
    d = WIKI_PATH / subdir
    if not d.exists():
        return []
    exclude = exclude_stems or set()
    return sorted(
        f.stem for f in d.glob("*.md")
        if f.is_file() and f.stem not in exclude
    )


def load_wiki(
    industry: Optional[str] = None,
    hall_type: Optional[str] = None,
    include_competitors: bool = False,
    include_policies: bool = False,
    include_credentials: bool = False,
    include_clients: bool = True,
    max_chars: Optional[int] = None,
) -> str:
    chunks = []

    for d in ALWAYS_LOAD:
        chunks.extend(load_directory(WIKI_PATH / d))

    if industry:
        chunks.extend(load_single_md(WIKI_PATH / "industries" / f"{industry}.md"))
    if hall_type:
        chunks.extend(load_single_md(WIKI_PATH / "hall-types" / f"{hall_type}.md"))
    if include_competitors:
        chunks.extend(load_directory(WIKI_PATH / "competitors"))
    if include_policies:
        chunks.extend(load_directory(WIKI_PATH / "policies"))
    if include_credentials:
        chunks.extend(load_directory(WIKI_PATH / "credentials"))
    if include_clients:
        chunks.extend(load_directory(WIKI_PATH / "clients"))

    content = "\n\n---\n\n".join(chunks)
    limit = max_chars if max_chars is not None else MAX_WIKI_CHARS
    if len(content) > limit:
        content = content[:limit] + "\n\n[内容已截断，仅显示部分知识库]"
    return content or "（知识库暂无相关内容，请先完成知识入库）"


# ─── Pydantic 模型 ────────────────────────────────────────────

class LoginRequest(BaseModel):
    name: str
    password: str


class StructuredQuery(BaseModel):
    su_name: str
    opportunity_name: str
    industry: Optional[str] = None
    hall_type: Optional[str] = None
    project_type: Optional[str] = None
    include_competitors: bool = False
    include_policies: bool = False
    include_credentials: bool = False
    extra_question: Optional[str] = None


class ChatMessage(BaseModel):
    message: str


class PromptUpdate(BaseModel):
    prompt: str


class FeedbackCreate(BaseModel):
    usage_log_id: int
    rating: int  # 1=赞 / -1=踩
    comment: Optional[str] = None


class UserCreate(BaseModel):
    name: str
    su_name: str
    role: str = "user"
    password: str


class UserUpdate(BaseModel):
    name: str
    su_name: str
    role: str


class PasswordUpdate(BaseModel):
    password: str


class SuNameCreate(BaseModel):
    name: str


class EstimationFileMeta(BaseModel):
    display_name: str
    category: str


# ─── 路由：主页 ──────────────────────────────────────────────

@app.get("/")
async def index():
    return HTMLResponse(Path("static/index.html").read_text(encoding="utf-8"))


# ─── 路由：认证 ──────────────────────────────────────────────

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT id, name, su_name, role, password_hash FROM users WHERE name = ?",
        (req.name,),
    ).fetchone()
    conn.close()

    if not row or not verify_password(req.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token({
        "user_id": row["id"],
        "name": row["name"],
        "su_name": row["su_name"],
        "role": row["role"],
    })
    return {"token": token, "name": row["name"], "su_name": row["su_name"], "role": row["role"]}


@app.get("/api/auth/me")
async def me(current_user: dict = Depends(get_current_user)):
    return {
        "user_id": current_user["user_id"],
        "name": current_user["name"],
        "su_name": current_user["su_name"],
        "role": current_user["role"],
    }


# ─── 路由：Wiki 选项（动态下拉） ──────────────────────────────

@app.get("/api/wiki-options")
async def wiki_options(_: dict = Depends(get_current_user)):
    exclude = {"index"}
    return {
        "industries": scan_wiki_dir("industries", exclude),
        "hall_types": scan_wiki_dir("hall-types", exclude),
        "project_types": ["新建", "改造升级", "咨询规划", "运营维护"],
    }


# ─── 路由：方案查询 ───────────────────────────────────────────

@app.post("/api/query")
async def structured_query(req: StructuredQuery, current_user: dict = Depends(get_current_user)):
    wiki_content = load_wiki(
        industry=req.industry,
        hall_type=req.hall_type,
        include_competitors=req.include_competitors,
        include_policies=req.include_policies,
        include_credentials=req.include_credentials,
        include_clients=req.include_credentials,
    )

    needs = []
    if req.include_competitors:
        needs.append("竞品参考")
    if req.include_policies:
        needs.append("政策依据")
    if req.include_credentials:
        needs.append("资质证书/案例")

    template = load_query_prompt()
    extra_line = f"- 补充说明：{req.extra_question}\n" if req.extra_question else ""
    user_prompt = template.format_map({
        "industry": req.industry or "不限",
        "hall_type": req.hall_type or "不限",
        "project_type": req.project_type or "不限",
        "needs_str": ", ".join(needs) if needs else "历史案例、功能模块",
        "extra_question_line": extra_line,
    })

    files = list_source_files()
    file_context = ""
    if files:
        file_list = "\n".join(f"- {stem}" for stem in sorted(files.keys()))
        file_context = (
            "\n\n可供用户下载的原始方案文件清单（若某案例有对应文件，"
            "请在提及时用 [[FILE:文件名]] 标注，文件名不含扩展名）：\n"
            + file_list
        )

    result = await _call_llm(user_prompt, wiki_content, file_context)

    # 写入使用记录
    conn = get_db_connection()
    cursor = conn.execute(
        """INSERT INTO usage_logs
           (user_id, user_name, su_name, function, opportunity_name, query_params)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            current_user["user_id"],
            current_user["name"],
            current_user["su_name"],
            "方案查询",
            req.opportunity_name,
            json.dumps({
                "industry": req.industry,
                "hall_type": req.hall_type,
                "project_type": req.project_type,
                "include_competitors": req.include_competitors,
                "include_policies": req.include_policies,
                "include_credentials": req.include_credentials,
            }, ensure_ascii=False),
        ),
    )
    usage_log_id = cursor.lastrowid
    conn.commit()
    conn.close()

    result["usage_log_id"] = usage_log_id
    return result


# ─── 路由：随手问 ─────────────────────────────────────────────

@app.post("/api/chat")
async def free_chat(req: ChatMessage, _: dict = Depends(get_current_user)):
    wiki_content = load_wiki(
        include_competitors=True,
        include_policies=True,
        include_credentials=True,
        include_clients=False,
        max_chars=MAX_CHAT_WIKI_CHARS,
    )
    return await _call_llm(req.message, wiki_content)


# ─── LLM 调用 ─────────────────────────────────────────────────

async def _call_llm(user_prompt: str, wiki_content: str, file_context: str = "") -> dict:
    system_prompt = (
        "你是公司内部展厅方案知识库助手，专门为方案人员提供专业支持。\n\n"
        "以下是公司内部知识库完整内容：\n\n"
        f"{wiki_content}\n\n"
        "工作原则：\n"
        "- 优先基于知识库内容回答，不编造案例或数据\n"
        "- 知识库无相关信息时，明确说明并给出通用行业建议\n"
        "- 回答结构清晰，适合直接用于方案参考\n"
        "- 使用专业但通俗的语言，避免过于学术化"
        + file_context
    )
    try:
        client, model = get_llm_client()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=3000,
        )
        return {"result": response.choices[0].message.content}
    except Exception as e:
        logger.exception("LLM 调用失败")
        raise HTTPException(status_code=500, detail=f"LLM调用失败：{str(e)}")


# ─── 路由：源文件 ─────────────────────────────────────────────

@app.get("/api/files")
async def list_files(_: dict = Depends(get_current_user)):
    files = list_source_files()
    return [
        {"stem": stem, "filename": info["filename"], "ext": info["ext"], "has_pdf": info["has_pdf"]}
        for stem, info in sorted(files.items())
    ]


@app.get("/api/files/{stem}/preview")
async def preview_file(stem: str, _: dict = Depends(get_current_user)):
    """PDF 在线预览（inline）"""
    if not SOURCE_FILES_DIR.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    pdf_path = SOURCE_FILES_DIR / f"{stem}.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="该文件无 PDF 预览版本")
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )


@app.get("/api/files/{stem}")
async def download_file(stem: str, current_user: dict = Depends(get_current_user)):
    """下载源文件（优先 PPT）"""
    files = list_source_files()
    if stem not in files:
        raise HTTPException(status_code=404, detail=f"文件不存在：{stem}")
    file_path = SOURCE_FILES_DIR / files[stem]["filename"]
    # 记录下载行为
    try:
        conn = get_db_connection()
        conn.execute(
            """INSERT INTO usage_logs (user_id, user_name, su_name, function, opportunity_name)
               VALUES (?, ?, ?, ?, ?)""",
            (current_user["user_id"], current_user["name"], current_user["su_name"],
             "文件下载", files[stem]["filename"]),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass
    return FileResponse(
        path=str(file_path),
        filename=files[stem]["filename"],
        media_type="application/octet-stream",
    )


# ─── 路由：反馈 ──────────────────────────────────────────────

@app.post("/api/feedback")
async def submit_feedback(req: FeedbackCreate, current_user: dict = Depends(get_current_user)):
    if req.rating not in (1, -1):
        raise HTTPException(status_code=400, detail="rating 必须为 1 或 -1")
    conn = get_db_connection()
    conn.execute(
        """INSERT INTO feedback (user_id, user_name, usage_log_id, rating, comment)
           VALUES (?, ?, ?, ?, ?)""",
        (current_user["user_id"], current_user["name"], req.usage_log_id, req.rating, req.comment),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


# ─── 路由：方案概算文件（普通用户） ──────────────────────────

@app.get("/api/estimation-files")
async def list_estimation_files(_: dict = Depends(get_current_user)):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id, display_name, filename, category, created_at FROM estimation_files ORDER BY category, display_name"
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        item = dict(r)
        item["previewable"] = item["filename"].lower().endswith(".pdf")
        result.append(item)
    return result


@app.get("/api/estimation-files/{file_id}/preview")
async def preview_estimation_file(file_id: int, _: dict = Depends(get_current_user)):
    """概算文件 PDF 在线预览（inline）"""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT filename FROM estimation_files WHERE id = ?", (file_id,)
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="文件不存在")
    if not row["filename"].lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="该文件无 PDF 预览（请上传 PDF 版本）")
    file_path = ESTIMATION_FILES_DIR / row["filename"]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件已丢失，请联系管理员")
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )


@app.get("/api/estimation-files/{file_id}/download")
async def download_estimation_file(file_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT filename, display_name FROM estimation_files WHERE id = ?", (file_id,)
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="文件不存在")
    file_path = ESTIMATION_FILES_DIR / row["filename"]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件已丢失，请联系管理员")
    ext = Path(row["filename"]).suffix
    download_name = row["display_name"] + ext
    # 记录下载行为
    try:
        conn2 = get_db_connection()
        conn2.execute(
            """INSERT INTO usage_logs (user_id, user_name, su_name, function, opportunity_name)
               VALUES (?, ?, ?, ?, ?)""",
            (current_user["user_id"], current_user["name"], current_user["su_name"],
             "概算文件下载", download_name),
        )
        conn2.commit()
        conn2.close()
    except Exception:
        pass
    return FileResponse(
        path=str(file_path),
        filename=download_name,
        media_type="application/octet-stream",
    )


# ─── 路由：管理后台 - Prompt ──────────────────────────────────

@app.get("/api/admin/prompt")
async def get_prompt(_: dict = Depends(require_admin)):
    return {"prompt": load_query_prompt(), "variables": PROMPT_VARIABLES}


@app.put("/api/admin/prompt")
async def update_prompt(req: PromptUpdate, _: dict = Depends(require_admin)):
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    (PROMPTS_DIR / "query_prompt.md").write_text(req.prompt, encoding="utf-8")
    return {"status": "ok"}


@app.get("/api/admin/prompt/default")
async def get_default_prompt(_: dict = Depends(require_admin)):
    return {"prompt": DEFAULT_QUERY_PROMPT}


@app.delete("/api/admin/prompt")
async def delete_prompt(_: dict = Depends(require_admin)):
    prompt_file = PROMPTS_DIR / "query_prompt.md"
    if prompt_file.exists():
        prompt_file.unlink()
    return {"status": "ok", "prompt": DEFAULT_QUERY_PROMPT}


# ─── 路由：管理后台 - 用户管理 ───────────────────────────────

@app.get("/api/admin/users")
async def list_users(_: dict = Depends(require_admin)):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id, name, su_name, role, created_at FROM users ORDER BY created_at"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/admin/users")
async def create_user(req: UserCreate, _: dict = Depends(require_admin)):
    if req.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="role 必须为 admin 或 user")
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO users (name, su_name, role, password_hash) VALUES (?, ?, ?, ?)",
            (req.name, req.su_name, req.role, hash_password(req.password)),
        )
        conn.commit()
    except Exception:
        raise HTTPException(status_code=400, detail="用户名已存在")
    finally:
        conn.close()
    return {"status": "ok"}


@app.put("/api/admin/users/{user_id}")
async def update_user(user_id: int, req: UserUpdate, current_user: dict = Depends(require_admin)):
    if req.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="role 必须为 admin 或 user")
    conn = get_db_connection()
    row = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="用户不存在")
    conn.execute(
        "UPDATE users SET name = ?, su_name = ?, role = ? WHERE id = ?",
        (req.name, req.su_name, req.role, user_id),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.delete("/api/admin/users/{user_id}")
async def delete_user(user_id: int, current_user: dict = Depends(require_admin)):
    if user_id == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="不能删除当前登录用户")
    conn = get_db_connection()
    row = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="用户不存在")
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.put("/api/admin/users/{user_id}/password")
async def change_password(user_id: int, req: PasswordUpdate, _: dict = Depends(require_admin)):
    if not req.password or len(req.password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少 6 位")
    conn = get_db_connection()
    row = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="用户不存在")
    conn.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (hash_password(req.password), user_id),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


# ─── 路由：管理后台 - SU 名称管理 ────────────────────────────

@app.get("/api/admin/su-names")
async def list_su_names(_: dict = Depends(require_admin)):
    conn = get_db_connection()
    rows = conn.execute("SELECT id, name FROM su_names ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/admin/su-names")
async def create_su_name(req: SuNameCreate, _: dict = Depends(require_admin)):
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="SU名称不能为空")
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO su_names (name) VALUES (?)", (req.name.strip(),))
        conn.commit()
    except Exception:
        raise HTTPException(status_code=400, detail="该SU名称已存在")
    finally:
        conn.close()
    return {"status": "ok"}


@app.delete("/api/admin/su-names/{su_id}")
async def delete_su_name(su_id: int, _: dict = Depends(require_admin)):
    conn = get_db_connection()
    conn.execute("DELETE FROM su_names WHERE id = ?", (su_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


# ─── 路由：管理后台 - 概算文件管理 ───────────────────────────

ESTIMATION_CATEGORIES = ["展厅新建", "展厅升级", "展厅运营"]


@app.post("/api/admin/estimation-files")
async def upload_estimation_file(
    display_name: str = Form(...),
    category: str = Form(...),
    file: UploadFile = File(...),
    _: dict = Depends(require_admin),
):
    if category not in ESTIMATION_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"category 必须为 {ESTIMATION_CATEGORIES}")
    if not display_name.strip():
        raise HTTPException(status_code=400, detail="display_name 不能为空")

    # 保存文件，使用安全文件名（时间戳前缀避免冲突）
    ext = Path(file.filename).suffix if file.filename else ""
    safe_filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}"
    dest = ESTIMATION_FILES_DIR / safe_filename
    content = await file.read()
    dest.write_bytes(content)

    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO estimation_files (display_name, filename, category) VALUES (?, ?, ?)",
            (display_name.strip(), safe_filename, category),
        )
        conn.commit()
    except Exception:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="文件名已存在，请重命名后上传")
    finally:
        conn.close()
    return {"status": "ok"}


@app.put("/api/admin/estimation-files/{file_id}")
async def update_estimation_file(
    file_id: int, req: EstimationFileMeta, _: dict = Depends(require_admin)
):
    if req.category not in ESTIMATION_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"category 必须为 {ESTIMATION_CATEGORIES}")
    conn = get_db_connection()
    row = conn.execute("SELECT id FROM estimation_files WHERE id = ?", (file_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="文件不存在")
    conn.execute(
        "UPDATE estimation_files SET display_name = ?, category = ? WHERE id = ?",
        (req.display_name.strip(), req.category, file_id),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.delete("/api/admin/estimation-files/{file_id}")
async def delete_estimation_file(file_id: int, _: dict = Depends(require_admin)):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT filename FROM estimation_files WHERE id = ?", (file_id,)
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="文件不存在")
    filename = row["filename"]
    conn.execute("DELETE FROM estimation_files WHERE id = ?", (file_id,))
    conn.commit()
    conn.close()
    (ESTIMATION_FILES_DIR / filename).unlink(missing_ok=True)
    return {"status": "ok"}


# ─── 路由：管理后台 - 使用记录 ───────────────────────────────

@app.get("/api/admin/usage-logs")
async def get_usage_logs(
    user_name: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100,
    _: dict = Depends(require_admin),
):
    query = """
        SELECT ul.id, ul.user_name, ul.su_name, ul.function,
               ul.opportunity_name, ul.query_params, ul.created_at,
               f.rating, f.comment
        FROM usage_logs ul
        LEFT JOIN feedback f ON f.usage_log_id = ul.id
        WHERE 1=1
    """
    params = []
    if user_name:
        query += " AND ul.user_name LIKE ?"
        params.append(f"%{user_name}%")
    if date_from:
        query += " AND ul.created_at >= ?"
        params.append(date_from)
    if date_to:
        query += " AND ul.created_at <= ?"
        params.append(date_to + " 23:59:59")
    query += " ORDER BY ul.created_at DESC LIMIT ?"
    params.append(limit)

    conn = get_db_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── 路由：诊断（公开） ───────────────────────────────────────

@app.get("/api/health")
async def health_check():
    model = None
    try:
        client, model = get_llm_client()
        client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5,
        )
        return {
            "status": "ok",
            "provider": LLM_PROVIDER,
            "model": model,
            "wiki_path": str(WIKI_PATH),
            "wiki_exists": WIKI_PATH.exists(),
            "source_files_dir": str(SOURCE_FILES_DIR),
            "source_files_count": len(list_source_files()),
        }
    except Exception as e:
        return {"status": "error", "provider": LLM_PROVIDER, "model": model, "error": str(e)}


@app.get("/api/wiki-stats")
async def wiki_stats():
    if not WIKI_PATH.exists():
        return {"total": 0, "breakdown": {}, "wiki_path": str(WIKI_PATH)}
    stats = {}
    total = 0
    for subdir in sorted(WIKI_PATH.iterdir()):
        if subdir.is_dir():
            count = len(list(subdir.glob("**/*.md")))
            stats[subdir.name] = count
            total += count
    return {"total": total, "breakdown": stats, "wiki_path": str(WIKI_PATH)}
