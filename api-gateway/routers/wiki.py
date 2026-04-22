"""
Wiki 信息路由：GET /v1/wiki/*
提供知识库元数据浏览能力，不调用 LLM。
所有可用选项均动态扫描 wiki/ 目录得出，不硬编码任何领域值。
"""
import os
from typing import Optional

from fastapi import APIRouter, Depends, Query

from auth import AppContext, get_app_context
from wiki_reader import list_entities, scan_options, wiki_stats

router = APIRouter(prefix="/v1/wiki", tags=["知识库信息"])

# 可通过 WIKI_EXTRA_OPTIONS 向 /v1/wiki/options 追加自定义选项组
# 格式：JSON，如 {"project_types":["新建","改造升级"]}
# 留空则响应中不包含自定义选项组，完全由 wiki 目录结构驱动
import json as _json
_extra_options: dict = {}
_raw_extra = os.getenv("WIKI_EXTRA_OPTIONS", "").strip()
if _raw_extra:
    try:
        _extra_options = _json.loads(_raw_extra)
    except Exception:
        pass


@router.get(
    "/options",
    summary="获取可用选项",
    description=(
        "动态扫描知识库目录，返回现有实体的枚举值，适合用于前端下拉菜单。\n\n"
        "结果完全由 `wiki/` 目录结构驱动，与领域无关。\n\n"
        "**所需权限**：`wiki`"
    ),
)
async def get_options(ctx: AppContext = Depends(get_app_context)) -> dict:
    ctx.require_scope("wiki")
    # 动态扫描 wiki/ 下所有子目录，各目录的词条名即为可用选项
    options = {
        subdir: scan_options(subdir, exclude={"index"})
        for subdir in ("industries", "hall-types", "competitors",
                       "policies", "credentials", "clients",
                       "modules", "proposal-stages")
        if scan_options(subdir)  # 目录不存在或为空则省略
    }
    # 合并管理员在环境变量中追加的自定义选项组
    options.update(_extra_options)
    return options


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
