"""
Wiki 信息路由：GET /v1/wiki/*
提供知识库元数据浏览能力，不调用 LLM。
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from auth import AppContext, get_app_context
from wiki_reader import list_entities, scan_options, wiki_stats

router = APIRouter(prefix="/v1/wiki", tags=["知识库信息"])


@router.get(
    "/options",
    summary="获取可用选项",
    description="返回知识库中现有的行业、展厅类型等枚举值，适合用于前端动态下拉菜单。\n\n**所需权限**：`wiki`",
)
async def get_options(ctx: AppContext = Depends(get_app_context)) -> dict:
    ctx.require_scope("wiki")
    return {
        "industries": scan_options("industries", exclude={"index"}),
        "hall_types": scan_options("hall-types", exclude={"index"}),
        "project_types": ["新建", "改造升级", "咨询规划", "运营维护"],
    }


@router.get(
    "/stats",
    summary="知识库统计",
    description="返回知识库各子目录的文件数量统计，用于监控知识库规模。\n\n**所需权限**：`wiki`",
)
async def get_stats(ctx: AppContext = Depends(get_app_context)) -> dict:
    ctx.require_scope("wiki")
    return wiki_stats()


@router.get(
    "/entities",
    summary="实体元数据列表",
    description=(
        "列出知识库中所有（或指定子目录的）实体的 frontmatter 元数据，"
        "可用于构建知识图谱或实体索引。\n\n"
        "**所需权限**：`wiki`"
    ),
)
async def get_entities(
    subdir: Optional[str] = Query(None, description="限定子目录，如 industries / modules，不填则返回全部"),
    ctx: AppContext = Depends(get_app_context),
) -> list[dict]:
    ctx.require_scope("wiki")
    return list_entities(subdir)
