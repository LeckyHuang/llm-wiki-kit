"""
Wiki 文件读取器
复用 wiki-app 中的知识库读取逻辑，支持：
- 生命周期过滤（archived 排除，outdated 加警示前缀）
- 按行业、展厅类型、场景过滤
- 字符数截断
"""
from pathlib import Path
from typing import Optional

import frontmatter as _frontmatter

from config import MAX_CHAT_WIKI_CHARS, MAX_WIKI_CHARS, WIKI_PATH

ALWAYS_LOAD = ["modules", "proposal-stages"]
_OUTDATED_PREFIX = "⚠️ [此内容可能已过期，请核实后使用]\n\n"


# ─── 单文件读取 ───────────────────────────────────────────────
def _read_file(md_file: Path) -> Optional[str]:
    """读取 Markdown 文件，应用生命周期过滤。archived 返回 None，outdated 加前缀。"""
    try:
        raw = md_file.read_text(encoding="utf-8").strip()
        if not raw:
            return None
        post = _frontmatter.loads(raw)
        status = str(post.metadata.get("status", "active")).lower()
        if status == "archived":
            return None
        return (_OUTDATED_PREFIX + raw) if status == "outdated" else raw
    except Exception:
        return None


def _load_dir(dir_path: Path) -> list[str]:
    if not dir_path.exists():
        return []
    chunks = []
    for md_file in sorted(dir_path.glob("**/*.md")):
        text = _read_file(md_file)
        if text:
            chunks.append(f"### 【{md_file.stem}】\n{text}")
    return chunks


def _load_single(file_path: Path) -> list[str]:
    if not file_path.exists():
        return []
    text = _read_file(file_path)
    return [f"### 【{file_path.stem}】\n{text}"] if text else []


# ─── 扫描子目录可用选项 ───────────────────────────────────────
def scan_options(subdir: str, exclude: set[str] | None = None) -> list[str]:
    """返回指定子目录中所有 .md 文件的 stem 列表（供下拉菜单）"""
    d = WIKI_PATH / subdir
    if not d.exists():
        return []
    exc = exclude or set()
    return sorted(f.stem for f in d.glob("*.md") if f.is_file() and f.stem not in exc)


# ─── 实体元数据列表 ───────────────────────────────────────────
def list_entities(subdir: str | None = None) -> list[dict]:
    """
    扫描 wiki/ 目录，返回所有实体的 frontmatter 元数据摘要。
    subdir 为 None 时扫描全部子目录。
    """
    base = WIKI_PATH
    dirs = [base / subdir] if subdir else [d for d in sorted(base.iterdir()) if d.is_dir()]
    result = []
    for d in dirs:
        if not d.exists():
            continue
        for md_file in sorted(d.glob("*.md")):
            try:
                raw = md_file.read_text(encoding="utf-8").strip()
                post = _frontmatter.loads(raw)
                meta = dict(post.metadata)
                meta["_file"] = md_file.stem
                meta["_dir"] = d.name
                result.append(meta)
            except Exception:
                pass
    return result


# ─── 核心：加载知识库 ─────────────────────────────────────────
def load_wiki(
    industry: Optional[str] = None,
    hall_type: Optional[str] = None,
    include_competitors: bool = False,
    include_policies: bool = False,
    include_credentials: bool = False,
    include_clients: bool = True,
    chat_mode: bool = False,
    max_chars: Optional[int] = None,
) -> str:
    chunks: list[str] = []

    # 必加模块
    for d in ALWAYS_LOAD:
        chunks.extend(_load_dir(WIKI_PATH / d))

    # 条件加载
    if industry:
        chunks.extend(_load_single(WIKI_PATH / "industries" / f"{industry}.md"))
    if hall_type:
        chunks.extend(_load_single(WIKI_PATH / "hall-types" / f"{hall_type}.md"))
    if include_competitors:
        chunks.extend(_load_dir(WIKI_PATH / "competitors"))
    if include_policies:
        chunks.extend(_load_dir(WIKI_PATH / "policies"))
    if include_credentials:
        chunks.extend(_load_dir(WIKI_PATH / "credentials"))
    if include_clients:
        chunks.extend(_load_dir(WIKI_PATH / "clients"))

    content = "\n\n---\n\n".join(chunks)
    limit = max_chars or (MAX_CHAT_WIKI_CHARS if chat_mode else MAX_WIKI_CHARS)
    if len(content) > limit:
        content = content[:limit] + "\n\n[内容已截断，仅显示部分知识库]"
    return content or "（知识库暂无相关内容，请先完成知识入库）"


# ─── 知识库统计 ───────────────────────────────────────────────
def wiki_stats() -> dict:
    if not WIKI_PATH.exists():
        return {"total": 0, "breakdown": {}, "wiki_path": str(WIKI_PATH)}
    breakdown: dict[str, int] = {}
    total = 0
    for sub in sorted(WIKI_PATH.iterdir()):
        if sub.is_dir():
            cnt = len(list(sub.glob("**/*.md")))
            breakdown[sub.name] = cnt
            total += cnt
    return {"total": total, "breakdown": breakdown, "wiki_path": str(WIKI_PATH)}
