# Query 操作提示词

> **适用路径**：AI 直接操作路径（Claude/Cursor）。  
> wiki 知识层不感知下游应用。本文件提供**通用查询**和**领域专用查询**两类模板，各下游应用按需选用或自行扩展。  
> 生命周期过滤规则对所有查询强制生效：`archived` 完全排除，`outdated` 降权提示。

将以下内容粘贴给 LLM，替换括号内参数后执行。

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
