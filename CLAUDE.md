# Claude Code 配置

请完整阅读 `schema/SCHEMA-CORE.md` 和 `schema/domain-config.xlsx`，按其中定义的目录结构、页面格式、版本管控规则和生命周期规则执行所有 wiki 操作。

> 行业枚举、字段清单、实体类型等领域配置均在 `schema/domain-config.xlsx` 中，Ingest 时必须读取。

## 快速操作入口

- **摄入新材料**：`prompts/ingest.md`
- **摄入经验报告**：`prompts/ingest-experience.md`
- **查询生产素材**：`prompts/query.md`（AI 直接操作路径）
- **健康检查**：`prompts/lint.md`
- **摄入经验材料**：`prompts/ingest-experience.md`

## 知识图谱（v2.5）

**在执行任何 Query 前**，先检查 `graphify-out/graph.json` 是否存在：
- 存在 → 使用 `/graphify query "关键词"` 定位相关节点子集，再在子集内检索
- 不存在 → 全量扫描 wiki/（图谱未初始化）

**图谱初始化**（首次，当 wiki 实体 > 150 页时）：
```
/graphify ./wiki --mode deep
```

**增量更新**（每次 Ingest 后自动触发，见各 ingest prompt 步骤 6）：
```
/graphify ./wiki --update
```

**图谱文件位置**：`graphify-out/`（graph.json / graph.html / GRAPH_REPORT.md 进 git，cache/ 不进）

**GRAPH_REPORT.md 优先**：执行 Query 前如果图谱已存在，先读 `graphify-out/GRAPH_REPORT.md` 了解整体知识结构，再决定查询路径。
