# Query 操作提示词

> **适用路径**：AI 直接操作路径（Claude/Cursor）。  
> 与 Web 应用路径（wiki-app/app.py `/api/query`）并行，变更查询逻辑需同步评估对方路径。  
> 差异对照：AI 路径输出完整素材包（7段结构）；Web 路径输出 LLM 合成回答。

将以下内容粘贴给 LLM，替换括号内参数后执行。

---

## 标准查询（为新方案生产提供素材）

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
