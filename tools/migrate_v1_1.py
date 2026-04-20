#!/usr/bin/env python3
"""
llm-wiki-kit v1.1 迁移脚本
为所有缺少 entity_id / version 的 wiki 条目补填这两个必填字段。

运行：python3 tools/migrate_v1_1.py
     加 --dry-run 参数可预览，不实际写入
"""

import re
import sys
from pathlib import Path
from collections import defaultdict

WIKI_DIR = Path(__file__).parent.parent / "wiki"
DRY_RUN = "--dry-run" in sys.argv

# 不处理的文件
SKIP_FILES = {"index.md", "_dashboard.md", "log.md", "credentials-index.md", "README.md"}

# industry 字段 → 中文缩写（取 / 前半段）
INDUSTRY_MAP = {
    "通信": "通信",
    "运营商": "通信",
    "教育": "教育",
    "科研": "教育",
    "工业": "工业",
    "制造": "工业",
    "能源": "能源",
    "电力": "能源",
    "矿业": "能源",
    "政府": "政务",
    "政务": "政务",
    "金融": "金融",
    "科技": "科技",
    "软件": "科技",
    "农业": "农业",
    "房地产": "地产",
    "楼宇": "地产",
}

# 城市关键词（按优先级排列，长的在前避免被短的覆盖）
CITIES = [
    "京津冀", "广东", "广州", "北京", "深圳", "湛江", "佛山", "揭阳",
    "广西", "安徽", "江门", "中山", "珠海", "香港", "国际",
]

# entity_id 类型前缀
TYPE_PREFIX = {
    "client": "client",
    "module": "module",
    "hall-type": "hall",
    "industry": "ind",
    "proposal-stage": "stage",
    "proposal_stage": "stage",   # 兼容下划线写法
    "competitor": "comp",
    "credential": "cred",
}


def get_field(fm_text: str, key: str) -> str:
    m = re.search(rf"^{key}:\s*(.+)$", fm_text, re.MULTILINE)
    return m.group(1).strip().strip('"').strip("'") if m else ""


def get_industry_short(fm_text: str) -> str:
    industry = get_field(fm_text, "industry")
    # 取 / 前的第一段，再映射
    first = industry.split("/")[0].strip()
    for k, v in INDUSTRY_MAP.items():
        if k in first:
            return v
    return "通用"


def get_city(fm_text: str, title: str) -> str:
    # 优先从 tags 找，再从 title 找
    tags_m = re.search(r"^tags:\s*\[(.+)\]", fm_text, re.MULTILINE)
    tags_text = tags_m.group(1) if tags_m else ""
    combined = tags_text + title
    for city in CITIES:
        if city in combined:
            return city
    return "通用"


def get_source_year(fm_text: str, fallback_created: str) -> str:
    # 尝试从 sources 字段中的文件名提取4位年份
    sources_line = get_field(fm_text, "sources")
    # 也尝试多行 sources 块
    block_m = re.search(r"^sources:(.+?)(?=^\w|\Z)", fm_text, re.MULTILINE | re.DOTALL)
    sources_text = block_m.group(1) if block_m else sources_line
    year_m = re.search(r"(20\d{2})", sources_text)
    if year_m:
        return year_m.group(1)
    return fallback_created[:4] if fallback_created else "未知"


def generate_entity_id(fm_text: str, etype: str, seq: int) -> str:
    prefix = TYPE_PREFIX.get(etype, etype)
    if etype == "client":
        created = get_field(fm_text, "created")
        year = get_source_year(fm_text, created)
        industry = get_industry_short(fm_text)
        title = get_field(fm_text, "title")
        city = get_city(fm_text, title)
        return f"client-{year}-{industry}-{city}-{seq:02d}"
    else:
        return f"{prefix}-{seq:02d}"


def insert_fields_after_status(fm_text: str, entity_id: str) -> str:
    lines = fm_text.split("\n")
    insert_at = len(lines)
    for i, line in enumerate(lines):
        if line.startswith("status:"):
            insert_at = i + 1
            break
    # 找不到 status 就插到 type 后面
    if insert_at == len(lines):
        for i, line in enumerate(lines):
            if line.startswith("type:"):
                insert_at = i + 1
                break
    lines.insert(insert_at, "version: v1")
    lines.insert(insert_at, f"entity_id: {entity_id}")
    return "\n".join(lines)


def process():
    # 第一步：收集所有待处理文件，按 type 分组
    files_by_type: dict[str, list] = defaultdict(list)

    for md_file in sorted(WIKI_DIR.rglob("*.md")):
        if "archive" in md_file.parts:
            continue
        if md_file.name in SKIP_FILES:
            continue

        text = md_file.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
        if not m:
            continue

        fm_text = m.group(1)
        if "entity_id:" in fm_text:
            continue  # 已有，跳过

        etype = get_field(fm_text, "type") or "unknown"
        etype = etype.replace("_", "-")  # 统一 proposal_stage → proposal-stage
        files_by_type[etype].append((md_file, fm_text, m, text))

    if not files_by_type:
        print("✓ 所有文件已是 v1.1 格式，无需更新")
        return

    # 第二步：逐类型生成 entity_id 并写入
    updated = 0
    for etype in sorted(files_by_type):
        items = files_by_type[etype]
        for seq, (md_file, fm_text, match, text) in enumerate(items, start=1):
            entity_id = generate_entity_id(fm_text, etype, seq)
            new_fm = insert_fields_after_status(fm_text, entity_id)
            new_text = text[: match.start(1)] + new_fm + text[match.end(1) :]

            rel = md_file.relative_to(WIKI_DIR)
            print(f"{'[DRY]' if DRY_RUN else '✓'} {rel}  →  entity_id: {entity_id}")

            if not DRY_RUN:
                md_file.write_text(new_text, encoding="utf-8")
            updated += 1

    action = "预览" if DRY_RUN else "更新"
    print(f"\n共{action} {updated} 个文件")
    if DRY_RUN:
        print("（使用不带 --dry-run 参数运行以实际写入）")


if __name__ == "__main__":
    process()
