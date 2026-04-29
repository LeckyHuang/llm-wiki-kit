# Ingest 操作提示词

> **适用路径**：AI 直接操作路径（Claude/Cursor）。  
> wiki 知识层不感知下游应用，Ingest 结果由各下游应用按需消费。变更后在 `wiki/log.md` 记录即可。

将以下内容粘贴给 LLM，替换 `[文件路径]` 后执行。

---

## 单文件 Ingest

```
请按照 schema/SCHEMA-CORE.md 的规则，处理以下新文件：

文件路径：[文件路径，例如 sources/proposals/001_湛江电信升级规划方案.pdf]

执行步骤：

【步骤 0：读取领域配置】
读取 schema/domain-config.xlsx：
- Sheet1：确认本次实体归属的目录位置
- Sheet2：确认本次 Ingest 需要提取的字段清单和枚举值

【步骤 1：解析文件元数据】
提取以下信息：
- 项目名 / 客户名 / 地点 / 日期
- 版本信号词（如"概念版"、"投标版"、"初稿"、"最终版"）
- 实体类型（对照 Sheet1）

【步骤 2：搜索现有 wiki 实体】
在 wiki/ 中查找是否存在同项目页面：
- 优先按 entity_id 精确匹配
- 若无 entity_id，按 title 模糊匹配（项目名+客户名）

【步骤 3a — 不存在：新建页面】
- 生成 entity_id（格式：{type_prefix}-{year}-{industry_abbr}-{city_abbr}-{seq:02d}）
- 按 Sheet2 字段清单提取所有字段
- 写入完整 frontmatter，version: v1，status: active
- sources 字段填入当前文件名
- 若文件为多媒体类型（视频/图片/HTML/PPT 等），在 frontmatter 中写入 assets 字段（type/label/path/url/description）
- 若 Sheet2 定义了 scenarios 字段，根据实体类型和内容填写适用场景标签
- 若同时提供了人工补充材料（sources/annotations/ 下的讲解词、问答对等），
  按 §2.2 正文分区约定写入对应 [type] 分区（[narration]/[qa]/[training] 等）

【步骤 3b — 已存在：版本比对与更新】
- 逐字段对比新旧值
- 有差异的字段：新值写入正文，旧值移入 history: 块（标注来源文件）
- 无差异的字段：保持不变
- sources 列表追加当前文件名（不覆盖旧记录）
- assets 列表追加新资产，不覆盖已有条目（同 path/url 则更新 description）
- 若提供了新的人工补充材料，更新对应 [type] 分区内容，旧版本移入 history 块
- version 递增（v1→v2→v3）

【步骤 4：更新关联页面】
- wiki/index.md（追加，不覆盖）
- 行业页、展厅类型页、功能模块页、方案阶段页（追加相关信息）
- 若有政策引用 → 检查 wiki/policies/ 是否已有，有则更新，无则新建
- wiki 页面间的所有引用必须使用 wikilink 格式：[[页面路径]]

【步骤 5：追加操作日志】
在 wiki/log.md 末尾追加：
[YYYY-MM-DD HH:MM] INGEST | sources/proposals/xxx.pdf | 新建/更新页面: [列表]
（若执行了版本更新，操作类型改为 VERSION-UPDATE）

---

【阶段二：自由发现扫描（v2.0）】

完成步骤 0–5 后，重新扫描原文件，寻找 domain-config.xlsx 未覆盖但具有反复出现或高业务价值的内容：

判断标准（满足任一即记录）：
- 在本文件中出现 2 次以上的结构化信息（数值、类型、名称等）
- 属于商业决策维度（预算区间、决策周期、采购触发事件等）
- 属于竞争情报维度（与友商差异、客户转换原因等）
- 属于执行经验维度（项目风险、交付难点、验收争议等）

发现后执行两步写入：

写入 1：在当前 wiki 页面 frontmatter 中追加 auto_discovered 块（不影响 schema 驱动字段）
```yaml
auto_discovered:
  - field: 建议字段名
    value: 发现的值
    context: 原文出处（一句话）
    confidence: high / medium
```

写入 2：在 wiki/schema-suggestions.md 中追加建议条目（若文件不存在则新建）
格式见 wiki/schema-suggestions.md 规范。

若本次未发现任何高价值字段，在日志中追加一行：
[YYYY-MM-DD HH:MM] INGEST | 自发现扫描：无新发现

---

【步骤 3b 补充：冲突检测（v2.0，仅版本更新时执行）】

在逐字段比对时，识别以下三类冲突：

Type A — 数值冲突（同字段，不同来源，值不同）
  → 新旧值并存，加 [CONFLICT] 标记，写入 pending-clarifications.md
  → 不阻断写入，继续更新其他字段

Type B — 定性矛盾（描述方向相反，如"系统稳定"vs"系统故障频发"）
  → 暂停写入该字段，将两种描述写入 pending-clarifications.md
  → 在 wiki 页面对应字段加 [PENDING] 标记，等待裁决

Type C — 逻辑矛盾（观点差异，如"该功能是优势"vs"该功能是短板"）
  → 两者均写入，各加 [PERSPECTIVE: 来源文件名] 标注
  → 在 pending-clarifications.md 备案（无需裁决，属观点差异）

写入 wiki/pending-clarifications.md 后，在日志追加：
[YYYY-MM-DD HH:MM] INGEST | 冲突检测：发现 N 条冲突 → pending-clarifications.md

【步骤 6：图谱增量更新（v2.5）】

检查 graphify-out/graph.json 是否存在：

若存在：
  执行：/graphify ./wiki --update
  （SHA256 缓存机制，仅处理本次变更的文件，成本极低）
  在 wiki/log.md 末尾追加：
  [YYYY-MM-DD HH:MM] GRAPH-UPDATE | 触发者: ingest | 更新文件: [本次新建/修改的 wiki 页面列表]

若不存在：
  跳过此步骤，在输出末尾提示：
  "图谱未初始化。当 wiki 实体超过 150 页时，手动执行首次建图：/graphify ./wiki --mode deep"

---

请先输出步骤 0-2 的分析确认（领域配置加载情况 + 实体匹配结果）后，再执行步骤 3-6 及阶段二。
完成后提示执行 Validate（见 prompts/validate.md）进行可视化验证。
```

---

## 批量 Ingest

```
请按照 schema/SCHEMA-CORE.md 的规则，批量处理 sources/proposals/ 目录下的所有新文件。

预备步骤：
- 读取 schema/domain-config.xlsx（Sheet1 + Sheet2）加载领域配置
- 扫描 wiki/clients/ 已有 entity_id 列表，建立匹配索引

处理顺序：按文件名序号从小到大。

每处理完一个文件，输出简要摘要：
- 文件名 | 操作类型（新建/VERSION-UPDATE）| entity_id | 更新字段数（若有版本更新）

全部处理完成后，输出汇总：
- 共处理文件数
- 新建 wiki 页面列表
- 版本更新页面列表（含新旧 version 号）
- 归入 history 块的字段变更统计
- 自发现字段建议数（已写入 schema-suggestions.md）
- 冲突检测结果（A/B/C 各类数量，已写入 pending-clarifications.md）
- 其他潜在问题（政策过期、枚举值不在 domain-config 中等）
```

---

## 友商方案 Ingest（竞品情报）

```
请按照 schema/SCHEMA-CORE.md 的规则，处理以下友商方案文件：

文件路径：[sources/competitors/xxx.pdf]

注意事项：
- 内容只写入 wiki/competitors/ 对应竞品页，不写入任何通用模板页
- 重点提取：技术方案特点、价格信号、话术风格、已知薄弱点
- 同样执行版本管控：若已存在同竞品页面，执行版本比对
- 操作日志操作类型：INGEST（新建）或 VERSION-UPDATE（更新）
```
