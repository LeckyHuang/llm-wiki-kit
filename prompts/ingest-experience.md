# Ingest Experience 操作提示词

> **适用路径**：AI 直接操作路径（Claude/Cursor）。  
> 用于摄入运营活动产生的**事件报告**（接待活动报告、运营月报、经验沉淀等），写入 `wiki/experiences/` 并触发跨实体增益。  
> 与 `prompts/ingest.md` 的区别：本 prompt 处理的是**动态事件型**记录，而非静态描述型文档。

将以下内容粘贴给 LLM，替换 `[文件路径]` 后执行。

---

```
请按照 schema/SCHEMA-CORE.md 的规则，处理以下事件报告文件：

文件路径：[文件路径，例如 sources/reports/2026-04-20-某客户接待报告.pdf]

执行步骤：

【步骤 0：前置检查 — 读取 wiki/config.yml】

读取 wiki/config.yml，检查 event_driven_ingest.enabled：

情况 A — enabled: false（或文件不存在）：
  进入手动模式。直接处理上方指定的文件路径，跳过扫描逻辑。

情况 B — enabled: true：
  扫描 watch_paths 中配置的目录（默认 sources/reports/），
  与 wiki/log.md 中已有的 EXPERIENCE-INGEST 记录比对，
  找出尚未摄入的文件，按 event_date（或文件名日期前缀）升序列出清单，
  等待用户确认处理哪些文件后继续。

同时读取 experience.auto_enrich 和 experience.enrichment_confirm，
记录增益行为配置，供步骤 5 使用。

---

【步骤 1：加载经验类型配置】

读取 schema/domain-config.xlsx：
- Experience Types Sheet：确认本次报告对应的 subtype（session / monthly / lesson 或其他行业定义的类型）
- 加载该 subtype 的核心维度字段（coreDimensions）和适用分区类型（applicableSections）
- Experience Section Types Sheet：加载各分区标签的含义、增益目标

输出确认：
- 报告文件 → 匹配到的 subtype 名称和缩写
- 本次需提取的维度字段列表
- 本次需提取的分区标签列表

---

【步骤 2：提取 Frontmatter】

从文件中提取以下信息：

基础字段（必填）：
- event_date：事件发生日期（非文件创建日期，取报告中的活动日期）
- title：事件标题（建议格式："YYYY-MM-DD [客户/主题] [subtype中文名]"）
- subtype：来自步骤 1 的确认值

维度字段（按 coreDimensions 逐项提取）：
- 按 domain-config Experience Types Sheet 定义的字段名逐一提取
- 若报告中无对应信息，填写 null，不跳过字段

关联实体（subject）：
- 扫描报告正文，识别提及的客户名、模块名
- 与 wiki/clients/ 和 wiki/modules/ 中的现有实体进行名称匹配
- 写入 subject 字段（格式：clients/实体文件名.md）
- 若有无法匹配的实体名，输出警告，不阻断流程

资产引用（exhibited_assets）：
- 提取本次活动中实际使用的媒体资产（视频名称、展项编号等）
- 与 sources/media/ 已有文件比对，填入 path 字段
- 无法匹配的资产仅记录 label，path 留空

生成 entity_id：
- 格式：exp-{event_year}-{subtype_abbr}-{seq:02d}
- 扫描 wiki/experiences/{subtype}/ 目录下现有文件，取最大序号 +1
- 若目录为空，seq 从 01 开始

---

【步骤 3：提取正文分区】

按步骤 1 加载的 applicableSections，逐分区提取内容：

每个分区的写入要求：
- 内容具体、可引用，保留原文表达
- 不做主观评价，不改写客观陈述
- 若报告中该分区信息不足，写明"（本次报告未包含此分区内容）"，不强行填充

分区格式（与现有 wiki 页面正文分区约定一致）：
[分区标签]
内容…

---

【步骤 4：写入 wiki/experiences/{subtype}/】

1. 按步骤 2 生成的 Frontmatter + 步骤 3 提取的正文，新建实体页面：
   路径：wiki/experiences/{subtype}/{entity_id}.md

2. 页面结构：
---
title: {title}
type: experience
entity_id: {entity_id}
subtype: {subtype}
event_date: {event_date}
status: active
created: {today}
updated: {today}
dimensions:
  {逐项列出}
subject:
  {列表}
exhibited_assets:
  {列表，无则留空列表}
sources:
  - {报告文件相对路径}
---

{按步骤 3 提取的各分区内容}

3. 在 wiki/log.md 末尾追加：
[YYYY-MM-DD HH:MM] EXPERIENCE-INGEST | {报告文件路径} | 新建: {entity_id} | subject: {关联实体列表}

---

【步骤 5：触发跨实体增益】

读取 wiki/config.yml 中 experience.auto_enrich：

若 auto_enrich: false：
  跳过增益，在日志追加：
  [YYYY-MM-DD HH:MM] EXPERIENCE-ENRICH | 跳过（auto_enrich: false）

若 auto_enrich: true：
  对 subject 字段中每一个关联实体，执行以下增益逻辑：

  ── 增益 A：[qa] 分区追加（来源：[qa-record] 分区）──
  条件：本次报告包含 [qa-record] 分区，且关联实体为 modules/ 类型
  操作：
    - 读取关联模块的 wiki 页面，找到 [qa] 分区（不存在则新建）
    - 将 [qa-record] 中每条 Q&A 追加至 [qa] 分区末尾
    - 每条追加内容末尾标注来源：（来源：{entity_id}，{event_date}）
    - 去重：若问题与已有条目高度相似（语义重复），不追加，仅在日志注明
    - 递增关联模块页 version

  ── 增益 B：[narration] 分区追加（来源：[narration-record] 分区）──
  条件：本次报告包含 [narration-record] 分区，且关联实体为 modules/ 类型
  操作：
    - 找到关联模块的 [narration] 分区（不存在则新建）
    - 追加实际话术片段，标注来源和角色（不记录讲解员姓名，仅记录角色）
    - 格式：> 实际话术内容（角色：{角色}，来源：{entity_id}，{event_date}）
    - 递增关联模块页 version

  ── 增益 C：scenarios 标签建议（来源：[visitor-insights] 分区）──
  条件：本次报告包含 [visitor-insights] 分区，且发现关联实体在新场景下有显著反应
  操作：
    - 不直接修改关联实体的 scenarios 字段
    - 在 wiki/schema-suggestions.md 追加建议条目：
      - 实体：{关联实体路径}
      - 建议追加 scenarios 标签：{建议值}
      - 依据：{visitor-insights 中的观察描述}（来源：{entity_id}）
    - 在日志注明已写入 schema-suggestions.md

  ── 增益 D：客户偏好更新（来源：客户关注点数据）──
  条件：subject 中包含 clients/ 类型实体，且报告包含客户关注点、兴趣点信息
  操作：
    - 读取对应客户页面，找到 preference_notes 段落（不存在则在正文末尾新建）
    - 追加本次接待中观察到的偏好描述，不覆盖已有内容
    - 格式：- {event_date} {偏好描述}（来源：{entity_id}）
    - 递增客户页 version

  若 enrichment_confirm: true：
    在执行增益前，展示本次将写入的所有变更列表，等待用户确认后再执行。
    格式：
    ──── 待执行增益变更 ────
    [增益A] modules/xxx.md → [qa] 分区追加 N 条
    [增益B] modules/xxx.md → [narration] 分区追加 N 段
    [增益C] schema-suggestions.md → scenarios 建议 N 条
    [增益D] clients/xxx.md → preference_notes 追加 N 条
    ────────────────────────
    确认执行？（输入 yes 继续）

  增益完成后，在 wiki/log.md 追加：
  [YYYY-MM-DD HH:MM] EXPERIENCE-ENRICH | {entity_id} | 增益A: {N}条 | 增益B: {N}段 | 增益C: {N}条建议 | 增益D: {N}条

---

【步骤 6：图谱增量更新（v2.5）】

检查 graphify-out/graph.json 是否存在：

若存在：
  执行：/graphify ./wiki --update
  在 wiki/log.md 末尾追加：
  [YYYY-MM-DD HH:MM] GRAPH-UPDATE | 触发者: experience-ingest | 更新文件: {entity_id} + 增益更新的关联实体列表

若不存在：
  跳过此步骤，在输出末尾提示：
  "图谱未初始化。当 wiki 实体超过 150 页或 experiences/ 超过 30 个 session 时，手动执行：/graphify ./wiki --mode deep"

---

请先输出步骤 0–1 的确认信息（config.yml 读取结果 + domain-config 加载的 subtype 和字段列表），
再依次执行步骤 2–6。
完成后提示执行 Lint（见 prompts/lint.md）确认 experience 实体生命周期状态正确。
```
