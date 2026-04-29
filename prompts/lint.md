# Lint 操作提示词

将以下内容粘贴给 LLM 执行健康检查。

---

## 完整 Lint（含生命周期检测）

```
请按照 schema/SCHEMA-CORE.md 的规则，对整个 wiki/ 目录执行健康检查。

今天日期：[填入当前日期，例如 2026-04-17]

检查项 1 — 过期政策（生命周期触发）：
- 读取 wiki/policies/ 所有页面的 valid_until 字段
- valid_until < 今天日期 → 将 status 改为 outdated，页面顶部加警告
- 如 valid_until 为空，标记为"长期有效，无需处理"

检查项 2 — 临期/过期证书（生命周期触发）：
- 读取 wiki/credentials/certificates/ 所有页面的 expiry_date 字段
- 距到期不足 90 天 → 将 status 改为 outdated，页面顶部加警告
- 已过 expiry_date → 将 status 改为 archived，输出归档建议（含建议的 archived_at 和 archive_reason）

检查项 3 — 归档建议（方案版本覆盖）：
- 检查 wiki/clients/ 中同一 entity_id 下 version < 最新版本的页面
- 若存在，输出归档建议（旧版本标记 archived，保留 history: 块）
- 注意：不自动执行归档，仅输出建议，等待用户确认

检查项 4 — 孤立页面：
- wiki/ 中无任何其他页面交叉引用（wikilink）的页面 → 列出待处理

检查项 5 — 内容矛盾：
- 同一功能模块在不同 wiki 页面的描述存在明显矛盾 → 列出待人工确认

检查项 6 — 空页面：
- 内容为空或极少（< 100 字）的页面 → 列出

检查项 7 — 冲突积压（v2.0）：
- 读取 wiki/pending-clarifications.md，统计待裁决条目数量
- 若有积压条目，按类型（Type A/B/C）分类列出
- Type B（定性矛盾）优先提示：其对应 wiki 字段标有 [PENDING]，影响 Query 准确性
- 输出每条条目的涉及实体、冲突字段、发现时间

检查项 8 — Schema 建议积压（v2.0）：
- 读取 wiki/schema-suggestions.md，统计未处理建议数量
- 列出建议字段名、出现次数、置信度
- 提示：积压超过 10 条时建议安排一次 domain-config.xlsx 审阅

检查项 9 — 媒体资产索引聚合（v2.5）：
- 扫描所有 wiki 实体（含 experiences/ 子目录）的 frontmatter
- 提取 assets[] 字段（来自普通实体）和 exhibited_assets[] 字段（来自 experience 实体）
- 重新生成 wiki/assets/index.md，包含三个区段：
  1. 按类型检索：video / image / html / ppt / pdf / excel / link / diagram 分组，列出每个资产的标签、所属实体、文件路径或URL、描述
  2. 按实体检索：列出每个实体引用的全部资产
  3. 跨事件资产使用记录：统计每个资产在 exhibited_assets 中被引用的次数和最近事件 entity_id
- 更新 index.md 顶部的"最后更新"时间为今天日期

检查项 10 — 图谱 AMBIGUOUS 关系处理（v2.5，仅在 graphify-out/GRAPH_REPORT.md 存在时执行）：
- 读取 graphify-out/GRAPH_REPORT.md，提取所有标记为 AMBIGUOUS 的关系条目
- 与 wiki/pending-clarifications.md 中现有条目按实体对去重
- 将未记录的 AMBIGUOUS 关系追加写入 pending-clarifications.md，格式：
  ### [CONFLICT-GXXX] 图谱关系待澄清（来自 Graphify）
  - 实体A：{节点A wiki 路径}
  - 实体B：{节点B wiki 路径}
  - 疑似关系：{关系描述}
  - 置信度：{score}（AMBIGUOUS）
  - 建议裁决：[ ] 合并为同一实体  [ ] 保留，明确区分  [ ] 无关联
- 输出本次新增的 AMBIGUOUS 条目数量；若 GRAPH_REPORT.md 不存在，跳过并注明"图谱未初始化"

输出格式：
# Lint Report — [日期]

## 1. 过期政策 (N条)
| 页面路径 | valid_until | 建议处理 |
|---------|------------|---------|
| ...     | ...        | 标记 outdated |

## 2. 临期证书 (N条)
| 页面路径 | expiry_date | 剩余天数 | 建议处理 |

## 3. 过期证书（归档建议）(N条)
| 页面路径 | expiry_date | 建议 archived_at | 建议 archive_reason |

## 4. 版本归档建议 (N条)
| entity_id | 旧版本页面路径 | 当前最新版本 | 建议操作 |

## 5. 孤立页面 (N条)

## 6. 内容矛盾 (N条)

## 7. 空页面 (N条)

## 8. 冲突积压 (N条)
| 冲突ID | 涉及实体 | 冲突字段 | 类型 | 发现时间 | 紧急程度 |
|--------|---------|---------|------|---------|---------|
| ...    | ...     | ...     | B    | ...     | ⚠️ 影响Query |

## 9. Schema 建议积压 (N条)
| 建议字段名 | 出现次数 | 置信度 |
|-----------|---------|--------|

## 10. 媒体资产索引更新
已扫描实体数：N / 资产总条数：N / 各类型分布：video:N image:N html:N ...
wiki/assets/index.md 已更新（最后更新：YYYY-MM-DD）

## 11. 图谱 AMBIGUOUS 关系（本次新增 N 条）
| 冲突编号 | 实体A | 实体B | 疑似关系 | 置信度 |
|---------|------|------|---------|--------|
| CONFLICT-G001 | ... | ... | ... | 0.38 |
（若 GRAPH_REPORT.md 不存在，注明：图谱未初始化，跳过检查项 10）

---
输出报告后，逐项询问是否立即处理。
用户确认归档后，执行以下操作：
1. 将页面移入 wiki/archive/（保持原路径镜像）
2. 在 frontmatter 末尾追加 archived_at 和 archive_reason
3. 在 wiki/log.md 追加：[YYYY-MM-DD HH:MM] ARCHIVE | 页面路径 | 归档原因
```

---

## 快速 Lint（仅检查证书和政策有效期）

```
请检查 wiki/policies/ 和 wiki/credentials/certificates/ 中所有页面的有效期字段。
今天日期：[填入当前日期]

- 已过期的政策/证书：输出路径 + 过期时间，建议标记 outdated 或 archived
- 3个月内到期的：输出路径 + 到期时间，建议标记 outdated
- 其余：无需输出
```
