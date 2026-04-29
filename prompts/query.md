# Query 操作提示词

> **适用路径**：AI 直接操作路径（Claude/Cursor）。  
> wiki 知识层不感知下游应用。本文件提供**通用查询**和**领域专用查询**两类模板，各下游应用按需选用或自行扩展。  
> 生命周期过滤规则对所有查询强制生效：`archived` 完全排除，`outdated` 降权提示。

将以下内容粘贴给 LLM，替换括号内参数后执行。

---

## 图谱路由前置步骤（v2.5，所有查询必须执行）

```
【图谱路由检查】

检查 graphify-out/graph.json 是否存在：

情况 A — 文件存在（图谱已初始化）：
  执行：/graphify query "{本次查询的核心关键词}"
  → 取出返回的相关节点对应 wiki 页面路径列表（通常 10–30 页）
  → 后续查询仅在此页面子集内检索，跳过全量扫描
  → 在输出末尾注明："已启用图谱路由，加载 N 个相关节点"

情况 B — 文件不存在（图谱未初始化）：
  跳过图谱路由，继续全量扫描 wiki/ 目录
  （图谱初始化条件：wiki 实体超过 150 页，或 experiences/ 超过 30 个 session）
```

---

## 查询前置检查（v2.0，所有查询必须执行）

```
在执行任何查询前，先完成以下检查：

【前置步骤：冲突状态扫描】
读取 wiki/pending-clarifications.md（若文件存在）：

1. 列出与本次查询主题相关的未裁决冲突条目（按 entity_id 或关键词匹配）
2. 若存在相关冲突：
   - 在查询结果中，对涉及冲突字段的内容加 ⚠️【存在未裁决冲突，见 pending-clarifications.md #ID】标注
   - 不因冲突阻断查询，但须让用户知晓哪些内容存疑
3. 若本次查询中用户对冲突内容给出了明确判断：
   - 在查询结果末尾列出"冲突裁决建议"，供用户确认后写回 wiki
   - 格式：CONFLICT-XXX → 裁决方向：[用户判断] → 建议操作：[具体字段更新]

【前置步骤结束，继续执行正式查询】
```

---

## 通用查询（适用于任意下游场景）

```
请在 wiki/ 目录中查询以下需求，并严格遵守生命周期过滤规则：

查询需求：[自然语言描述需求，例如：找出所有适合政府参观接待的展项内容]

过滤条件（可选，填写适用的）：
- 实体类型（type）：[exhibit / client / policy / competitor / ...]
- 场景标签（scenarios）：[AI策展 / 智能问答 / 方案生产 / AI陪练 / ...]
- 行业（industry）：[参照 domain-config.xlsx Sheet2]
- 状态（status）：默认只返回 active；如需 outdated 请显式说明

生命周期规则（强制）：
- status: archived → 完全跳过，不引用
- status: outdated → 可引用，但在该条内容前加 ⚠️【此内容可能已过期，请核实】

输出要求：
- 匹配的 wiki 页面列表（含 entity_id、title、type、status）
- 每条页面的关键字段摘要
- 若页面包含 assets 字段，列出资产引用（type/label/url or path）
- 若页面包含所需正文分区（[narration]/[qa] 等），提取相关分区内容
- 每条注明来源 wiki 页面路径

若本次查询产生新洞察，在输出末尾列出建议回写内容，并在 wiki/log.md 追加：
[YYYY-MM-DD HH:MM] QUERY | [场景/关键词] | 产生洞察: [简述]
```

---

## 领域专用查询：方案生产素材包

```
请按照 schema/SCHEMA-CORE.md 的 Query 规则，为以下新方案生产查询相关素材：

- 客户行业：[参照 schema/domain-config.xlsx Sheet2 industry 枚举值]
- 项目类型：[新建/升级/运营/复合型]
- 展厅类型：[参照 domain-config.xlsx Sheet2 hall_type 枚举值]
- 方案阶段：[参照 domain-config.xlsx Sheet2 proposal_stage 枚举值]
- 客户层级：[集团级/省级/地市级/区域级]
- 特殊需求：[如有，填写；如无，填"无"]

生命周期过滤规则（必须遵守）：
- status: archived 的页面：完全跳过，不引用
- status: outdated 的页面：可引用，但在该条内容前加 ⚠️【此内容可能已过期，请核实后使用】

请输出：
1. 推荐方案框架（参考 wiki/proposal-stages/ 对应模板）
2. 行业痛点与话术（来自 wiki/industries/）
3. 适用功能模块及描述（来自 wiki/modules/）
4. 类似历史案例参考（来自 wiki/clients/，优先 result: 中标）
5. 竞品差异化定位建议（来自 wiki/competitors/，如有）
6. 适用政策依据（来自 wiki/policies/，仅 status: active 的）
7. 本项目所需资质清单（来自 wiki/credentials/credentials-index.md）

每条内容注明来源 wiki 页面。
若本次查询产生新洞察或修正了已有内容，在输出末尾列出建议回写的内容，并在 wiki/log.md 追加：
[YYYY-MM-DD HH:MM] QUERY | 行业/阶段/展厅类型 | 产生洞察: [简述]
```

---

## 领域专用查询：AI 策展配屏

```
请在 wiki/ 目录中，为以下接待活动匹配最适合的展项内容：

接待场景：[例如：政府领导参观，关注 5G+工业，预计 20 分钟]
客户画像：[例如：省级政府，技术背景弱，决策层]
可用时长：[分钟数]
展厅区域：[如有分区限制，填写；否则填"不限"]
特殊要求：[如有，填写；否则填"无"]

过滤规则（强制）：
- status: archived → 完全跳过
- status: outdated → 加 ⚠️ 提示后仍可参考
- 优先匹配 scenarios 字段包含"AI策展"的实体

输出：
1. 推荐展项列表（按建议播放顺序排列）
   - 每条：title / entity_id / 推荐理由 / 预计时长
2. 每个展项的 assets 列表（type / label / url or path）
3. 若展项包含 [narration] 分区，提取讲解词供导览使用
4. 总时长估算

每条注明来源 wiki 页面。
```

---

## 快速查询（单点问题）

```
请在 wiki/ 目录中查找关于「[关键词]」的相关内容。
注意：跳过 status: archived 的页面；status: outdated 的内容前加 ⚠️ 提示。
汇总输出，并注明来源页面。
```

---

## 竞品分析查询

```
请查询 wiki/competitors/ 目录，针对「[友商名称或"所有友商"]」输出：
1. 技术方案特点
2. 典型话术风格
3. 已知薄弱点
4. 我方差异化建议

注意：跳过 status: archived 的竞品页面。
```

---

## 资产检索查询（v2.5）

```
请在 wiki/ 目录中按媒体资产维度检索。

【优先路径】先读取 wiki/assets/index.md（若存在），直接从索引查询，无需扫描全库。
若 index.md 不存在或需要核实，实时扫描所有 wiki 实体的 assets[] 和 exhibited_assets[]。

查询条件（填写适用的，其余留空）：
- 资产类型：[video / image / html / ppt / pdf / excel / link / diagram / 全部]
- 关键词：[资产标签中的关键词，可选]
- 所属实体范围：[modules / clients / experiences / 全部]
- 使用频次筛选：[仅返回被 experience 引用超过 N 次的资产，可选]

输出：
1. 匹配资产列表
   每条：资产标签 / 类型 / 所属实体 / 文件路径或URL / 描述
2. 高频资产排行（按 exhibited_assets 引用次数降序，Top 10）
   用于评估哪些资产最受市场验证
3. 零引用资产列表
   从未出现在 experience.exhibited_assets 中的资产，评估是否需要更新或下线
4. 每条注明数据来源（wiki/assets/index.md 或实时扫描）
```

---

## Path B：对话式知识捕获（v2.1，每次 Query 会话结束时执行）

> 在以上任意查询模板执行完毕、用户不再追问后，自动执行以下捕获环节。  
> 若本次对话未产生任何知识修正或补充，直接结束，无需输出此模块。

```
【Path B：本次查询反馈捕获】

请回顾本次查询对话，识别以下三类知识事件：

类型 1 — 知识修正：用户纠正了 wiki 中现有描述（字段值有误、表述不准确等）
类型 2 — 知识空白：用户提到了 wiki 中尚未记录的信息（新字段、新数据等）
类型 3 — 表达偏好：用户明确表达了对某类受众的表述倾向（用词偏好、风格偏好等）

若存在上述任一类型，输出以下确认列表（若无则跳过整个模块）：

──── 本次对话知识捕获清单 ────

[序号]. [类型标签] 指向实体：{wiki 页面路径}
  {发现描述}
  → 选项 A：直接更新 wiki（写入 history 块，version 递增）
  → 选项 B：加入 wiki/schema-suggestions.md（等待 Schema 级确认）
  → 选项 C：忽略，仅本次有效

──────────────────────────────

请用户对每条选择处理方式（回复序号 + A/B/C，或直接说明）。

用户确认后执行对应操作：
- 选项 A：读取目标 wiki 页面 → 更新对应字段 → 旧值写入 history 块 → version 递增 → 写 log.md
  日志格式：[YYYY-MM-DD HH:MM] FEEDBACK | {wiki 页面路径} | 更新字段: {字段名} | 来源: 对话捕获
- 选项 B：在 wiki/schema-suggestions.md 末尾追加建议条目
- 选项 C：不执行任何操作

全部处理完成后，在 wiki/log.md 追加汇总行：
[YYYY-MM-DD HH:MM] FEEDBACK | 本次捕获: {N}条 | 直接更新: {n1}条 | 写入建议: {n2}条 | 忽略: {n3}条
```
