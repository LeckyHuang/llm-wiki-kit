"""
检索路由：POST /v1/retrieve
纯检索接口，返回原始知识片段，不调用 LLM 做总结。
支持两种查询模式：
- keyword（默认）：正则分词 + 模糊匹配，零 LLM 开销
- nlp：LLM 先解析自然语言意图 → 提取 entity_type/tags/关键词 → 精准检索
- 可选 LLM 相关性重排（rerank）
"""
import json as _json
import logging
import re
from pathlib import Path
from typing import Optional

import frontmatter as _frontmatter
from fastapi import APIRouter, Depends

from auth import AppContext, get_app_context
from config import WIKI_PATH
from llm_client import call_llm
from models.retrieve import RetrieveRequest, RetrieveResponse, RetrieveResult

router = APIRouter(prefix="/v1", tags=["知识库检索"])
logger = logging.getLogger(__name__)


# ─── 辅助：读取单个文件 ───────────────────────────────────────
def _read_entity(md_file: Path) -> Optional[dict]:
    try:
        raw = md_file.read_text(encoding="utf-8").strip()
        if not raw:
            return None
        post = _frontmatter.loads(raw)
        return {
            "path": str(md_file.relative_to(WIKI_PATH)),
            "dir": md_file.parent.name,
            "stem": md_file.stem,
            "frontmatter": dict(post.metadata),
            "body": post.content,
        }
    except Exception:
        return None


# ─── 辅助：分词（简单按非中/英文/数字字符切分）───────────────
def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[一-龥a-zA-Z0-9]+", text) if len(t) > 1]


# ─── 辅助：计算相关性得分 ─────────────────────────────────────
def _score_entity(entity: dict, query_tokens: list[str], req: RetrieveRequest) -> float:
    score = 0.0
    fm = entity.get("frontmatter", {})
    body = entity.get("body", "")
    title = str(fm.get("title", entity.get("stem", "")))

    # 1. 标题匹配（权重高）
    title_lower = title.lower()
    for tok in query_tokens:
        if tok in title_lower:
            score += 0.35

    # 2. 正文匹配（权重中）
    body_lower = body.lower()
    matched = sum(1 for tok in query_tokens if tok in body_lower)
    score += (matched / max(len(query_tokens), 1)) * 0.25

    # 3. tags 匹配（权重高）
    tags = fm.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    tag_set = {str(t).lower() for t in tags}
    tag_matched = sum(1 for tok in query_tokens if tok in tag_set)
    score += (tag_matched / max(len(query_tokens), 1)) * 0.30

    # 4. 摘要匹配（权重中）
    summary = str(fm.get("summary", "")).lower()
    for tok in query_tokens:
        if tok in summary:
            score += 0.10

    return min(score, 1.0)


# ─── 辅助：LLM 查询意图解析 ───────────────────────────────────

def _scan_entity_types() -> list[str]:
    """扫描 wiki/ 下所有子目录名，作为可用实体类型列表"""
    if not WIKI_PATH.exists():
        return []
    return sorted([
        d.name for d in WIKI_PATH.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ])


_QUERY_PARSE_PROMPT_TPL = """你是知识库检索意图解析器。用户输入自然语言查询，你需要分析意图并提取检索参数。

可用的实体类型（wiki/ 子目录）：{entity_types}

请仅输出 JSON（不要任何其他内容）：
{{"entity_type": "最匹配的实体类型或null", "keywords": ["关键词1", "关键词2"], "tags": ["标签1"]}}

规则：
- entity_type：从可用类型中选择最匹配的一个，无法判断则填 null
- keywords：从查询中提取 2-5 个核心检索关键词（优先提取专有名词、技术术语、场景描述词）
- tags：推测可能关联的标签，无把握则空数组"""


async def _llm_parse_query(query: str) -> dict:
    """用 LLM 解析自然语言查询，返回 {{entity_type, keywords, tags}}"""
    entity_types = _scan_entity_types()
    types_hint = ", ".join(entity_types) if entity_types else "（wiki/ 目录为空，暂无实体类型）"

    prompt = _QUERY_PARSE_PROMPT_TPL.format(entity_types=types_hint)
    try:
        raw = await call_llm(prompt, "", system_extra=f"用户查询：{query}", max_tokens=300)
        # 清理可能的 markdown 代码块包裹
        cleaned = raw.strip().strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        parsed = _json.loads(cleaned)
        return {
            "entity_type": parsed.get("entity_type") or None,
            "keywords": parsed.get("keywords", []),
            "tags": parsed.get("tags", []),
        }
    except Exception as e:
        logger.warning(f"LLM 查询解析失败，降级为关键词模式: {e}")
        return {"entity_type": None, "keywords": [], "tags": []}


# ─── 辅助：LLM 重排 ───────────────────────────────────────────
_RERANK_PROMPT_TPL = """请对以下知识库条目与查询的相关性进行评分。

查询：{query}

条目：
{items_text}

请仅输出 JSON 数组，格式如下：
[{{"index": 0, "score": 0.95}}, {{"index": 1, "score": 0.72}}, ...]
其中 index 对应条目顺序，score 为 0-1 之间的相关性得分。不要输出任何其他内容。"""


async def _llm_rerank(query: str, candidates: list[dict]) -> list[float]:
    if not candidates:
        return []
    items_text = "\n\n".join(
        f"[{i}] 标题：{c['frontmatter'].get('title', c['stem'])}\n类型：{c['dir']}\n内容摘要：{c['body'][:300]}..."
        for i, c in enumerate(candidates)
    )
    prompt = _RERANK_PROMPT_TPL.format(query=query, items_text=items_text)
    try:
        # rerank 不加载 wiki_content，system 传空
        raw = await call_llm(prompt, "", max_tokens=2000)
        arr = _json.loads(raw.strip().strip("`").replace("json", "").strip())
        scores = [0.5] * len(candidates)
        for item in arr:
            idx = item.get("index", -1)
            if 0 <= idx < len(candidates):
                scores[idx] = float(item.get("score", 0.5))
        return scores
    except Exception as e:
        logger.warning(f"LLM rerank 失败，降级为原始得分: {e}")
        return [c.get("_score", 0.5) for c in candidates]


# ─── 主路由 ───────────────────────────────────────────────────
@router.post(
    "/retrieve",
    response_model=RetrieveResponse,
    summary="纯检索：返回原始知识片段",
    description=(
        "按 query 和过滤条件检索知识库，返回原始 Markdown 片段，不调用 LLM 做总结。\n\n"
        "两种查询模式：\n"
        "- `keyword`（默认）：正则分词 + 模糊匹配，零 LLM 开销\n"
        "- `nlp`：LLM 先解析自然语言意图 → 自动提取 entity_type/tags/关键词 → 精准检索\n\n"
        "若 rerank=true，会用 LLM 对候选结果做相关性重排（消耗额外 token）。\n\n"
        "**所需权限**：`query`"
    ),
)
async def retrieve(
    req: RetrieveRequest,
    ctx: AppContext = Depends(get_app_context),
) -> RetrieveResponse:
    ctx.require_scope("query")

    # ── 0. LLM 查询意图解析（nlp 模式）─────────────────────
    entity_type = req.entity_type
    tags = req.tags
    if req.query_mode == "nlp":
        parsed = await _llm_parse_query(req.query)
        if parsed["entity_type"] and not entity_type:
            entity_type = parsed["entity_type"]
        if parsed["tags"] and not tags:
            tags = parsed["tags"]
        # nlp 模式：用解析出的关键词替代正则分词
        if parsed["keywords"]:
            query_tokens = [k.lower() for k in parsed["keywords"]]
        else:
            query_tokens = _tokenize(req.query)  # 降级
    else:
        query_tokens = _tokenize(req.query)

    # ── 1. 扫描所有实体 ──
    candidates: list[dict] = []
    base = WIKI_PATH
    dirs = []
    if entity_type:
        d = base / entity_type
        if d.exists():
            dirs = [d]
    else:
        dirs = [d for d in sorted(base.iterdir()) if d.is_dir() and not d.name.startswith(".")]

    for d in dirs:
        for md_file in sorted(d.rglob("*.md")):
            entity = _read_entity(md_file)
            if not entity:
                continue

            fm = entity.get("frontmatter", {})

            # 生命周期过滤
            status = str(fm.get("status", "active")).lower()
            if req.status and status != req.status.lower():
                continue
            if req.status == "active" and status == "archived":
                continue

            # tags 过滤（AND 关系）
            if tags:
                entity_tags = fm.get("tags", [])
                if isinstance(entity_tags, str):
                    entity_tags = [t.strip() for t in entity_tags.split(",") if t.strip()]
                entity_tag_set = {str(t).lower() for t in entity_tags}
                if not all(str(t).lower() in entity_tag_set for t in tags):
                    continue

            candidates.append(entity)

    # ── 2. 打分排序 ──
    for c in candidates:
        c["_score"] = _score_entity(c, query_tokens, req)

    # 过滤掉得分为 0 的（除非总数太少，保留部分）
    candidates = [c for c in candidates if c["_score"] > 0]
    candidates.sort(key=lambda x: x["_score"], reverse=True)

    # 取前 limit * 2 做 rerank 候选（如果开启 rerank）
    top_candidates = candidates[: req.limit * 2] if req.rerank else candidates[: req.limit]

    # ── 3. 可选 LLM 重排 ──
    if req.rerank and top_candidates:
        rerank_scores = await _llm_rerank(req.query, top_candidates)
        for c, s in zip(top_candidates, rerank_scores):
            c["_score"] = round(s, 4)
        top_candidates.sort(key=lambda x: x["_score"], reverse=True)

    final_candidates = top_candidates[: req.limit]

    # ── 4. 组装响应 ──
    results: list[RetrieveResult] = []
    total_chars = 0
    for c in final_candidates:
        fm = c.get("frontmatter", {})
        body = c.get("body", "")
        if len(body) > req.max_chars_per_result:
            body = body[: req.max_chars_per_result] + "\n\n[内容已截断]"
        total_chars += len(body)

        results.append(
            RetrieveResult(
                title=str(fm.get("title", c.get("stem", ""))),
                entity_type=c.get("dir", ""),
                source=c.get("path", ""),
                relevance_score=round(c.get("_score", 0.0), 4),
                frontmatter=fm,
                content=body,
            )
        )

    return RetrieveResponse(
        results=results,
        total=len(candidates),
        query=req.query,
        reranked=req.rerank,
        chars_used=total_chars,
    )
