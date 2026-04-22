"""
查询路由：POST /v1/query  /  POST /v1/chat

Prompt 优先级（从高到低）：
  1. 请求体中的 custom_prompt（调用方完全自定义）
  2. WIKI_QUERY_PROMPT_FILE 指定的文件（运维层配置）
  3. wiki-app 同目录的 prompts/query_prompt.md（复用已有配置）
  4. 内置通用 prompt（与领域无关的兜底模板）
"""
import os
from pathlib import Path

from fastapi import APIRouter, Depends

from auth import AppContext, get_app_context
from config import LLM_PROVIDER, WIKI_PATH
from llm_client import call_llm
from models.query import ChatRequest, QueryRequest, QueryResponse
from wiki_reader import load_wiki

router = APIRouter(prefix="/v1", tags=["知识库查询"])


# ─── Prompt 加载（通用兜底，不含任何领域词汇）────────────────
_GENERIC_QUERY_TPL = """请根据以下查询条件，从知识库中提取最相关的内容并整理输出：

- 行业 / 领域：{industry}
- 分类 / 类型：{hall_type}
- 项目阶段 / 类型：{project_type}
- 需要内容：{needs_str}
{extra_line}
请按以下结构输出（若知识库无相关内容可省略对应章节）：

## 相关案例
（从知识库中提炼3-5个最相关的案例，包含核心亮点和可借鉴之处）

## 推荐方案要素
（列出适合本次需求的关键模块、功能点或方法论）

## 方案框架建议
（基于知识库中的同类经验，给出结构化的方案骨架）

## 参考依据
（可引用的政策、标准、行业规范等，如无则省略）

## 竞品 / 市场参考
（同类竞争者的相关信息，如无则省略）

## 核心建议
（基于以上内容，给出2-3条可直接落地的建议）"""


def _load_query_prompt() -> str:
    """
    按优先级查找 prompt 文件，找到即返回，否则使用内置通用模板。
    """
    candidates = [
        # 1. 运维层显式指定的文件
        os.getenv("WIKI_QUERY_PROMPT_FILE", ""),
        # 2. wiki-app 目录下的自定义 prompt（与 wiki-app 共用配置）
        str(WIKI_PATH.parent / "wiki-app" / "prompts" / "query_prompt.md"),
        # 3. 项目根目录的 prompts/
        str(WIKI_PATH.parent / "prompts" / "query_prompt.md"),
    ]
    for path in candidates:
        if path:
            p = Path(path)
            if p.exists():
                try:
                    return p.read_text(encoding="utf-8")
                except Exception:
                    pass
    return _GENERIC_QUERY_TPL


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="结构化知识查询",
    description=(
        "按指定条件加载知识库，经 LLM 整理后返回结构化知识摘要。\n\n"
        "查询 prompt 优先使用 wiki 目录中已有的配置文件，"
        "无配置文件时自动降级为领域无关的通用模板。\n\n"
        "**所需权限**：`query`"
    ),
)
async def structured_query(
    req: QueryRequest,
    ctx: AppContext = Depends(get_app_context),
) -> QueryResponse:
    ctx.require_scope("query")

    wiki_content = load_wiki(
        industry=req.industry,
        hall_type=req.hall_type,
        include_competitors=req.include_competitors,
        include_policies=req.include_policies,
        include_credentials=req.include_credentials,
        include_clients=req.include_credentials,
    )

    if req.custom_prompt:
        # 调用方完全自定义 prompt，直接使用
        user_prompt = req.custom_prompt
    else:
        needs = []
        if req.include_competitors:
            needs.append("竞品参考")
        if req.include_policies:
            needs.append("政策依据")
        if req.include_credentials:
            needs.append("资质证书/案例")
        extra_line = f"- 补充说明：{req.question}\n" if req.question else ""
        template = _load_query_prompt()
        user_prompt = template.format_map({
            "industry": req.industry or "不限",
            "hall_type": req.hall_type or "不限",
            "project_type": req.project_type or "不限",
            "needs_str": ", ".join(needs) if needs else "案例、方案要素",
            "extra_line": extra_line,
        })

    result_text = await call_llm(user_prompt, wiki_content)
    return QueryResponse(
        result=result_text,
        wiki_chars_used=len(wiki_content),
        provider=LLM_PROVIDER,
    )


@router.post(
    "/chat",
    response_model=QueryResponse,
    summary="自由问答",
    description=(
        "针对知识库进行任意问题的对话式查询，加载更广泛的知识库内容。\n\n"
        "**所需权限**：`chat`"
    ),
)
async def free_chat(
    req: ChatRequest,
    ctx: AppContext = Depends(get_app_context),
) -> QueryResponse:
    ctx.require_scope("chat")

    wiki_content = load_wiki(
        include_competitors=True,
        include_policies=True,
        include_credentials=True,
        include_clients=False,
        chat_mode=True,
    )
    result_text = await call_llm(req.message, wiki_content)
    return QueryResponse(
        result=result_text,
        wiki_chars_used=len(wiki_content),
        provider=LLM_PROVIDER,
    )
