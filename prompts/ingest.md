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

请先输出步骤 0-2 的分析确认（领域配置加载情况 + 实体匹配结果）后，再执行步骤 3-5。
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
- 发现的潜在问题（政策过期、内容矛盾、枚举值不在 domain-config 中等）
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
