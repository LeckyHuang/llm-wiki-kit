"""
查询路由：POST /v1/query  /  POST /v1/chat
"""
from fastapi import APIRouter, Depends

from auth import AppContext, get_app_context
from config import LLM_PROVIDER
from llm_client import call_llm
from models.query import ChatRequest, QueryRequest, QueryResponse
from wiki_reader import load_wiki

router = APIRouter(prefix="/v1", tags=["知识库查询"])

# ─── 默认查询提示词模板 ────────────────────────────────────────
_DEFAULT_QUERY_TPL = """请为以下展厅方案需求提供知识库素材摘要：

- 行业：{industry}
- 展厅类型：{hall_type}
- 项目类型：{project_type}
- 需要内容：{needs_str}
{extra_line}
请从知识库中提取最相关内容，按以下结构输出：

## 相关历史案例
（3-5个，每个包含：项目名称、核心亮点、可借鉴之处）

## 推荐功能模块
（列出适合本项目的模块及简要说明）

## 方案框架
（从过往同类项目中提炼出通用方案结构骨架）

## 政策与依据
（可引用的政策文件或行业标准，如无则省略）

## 竞品参考
（友商在同类项目的策略，如无则省略）

## 方案建议
（基于以上内容，给出2-3条核心建议）"""


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="结构化知识查询",
    description=(
        "按行业、展厅类型等条件加载知识库，经 LLM 整理后返回方案素材摘要。\n\n"
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

    # 构造用户 prompt
    if req.custom_prompt:
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
        user_prompt = _DEFAULT_QUERY_TPL.format(
            industry=req.industry or "不限",
            hall_type=req.hall_type or "不限",
            project_type=req.project_type or "不限",
            needs_str=", ".join(needs) if needs else "历史案例、功能模块",
            extra_line=extra_line,
        )

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
