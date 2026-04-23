# wiki/experiences/ — 经验知识目录

本目录存放所有 `experience` 类型实体，记录运营活动产生的经验知识。

---

## 实体类型说明

| 子目录 | subtype | 触发时机 | entity_id 格式 |
|--------|---------|---------|--------------|
| `session/` | session | 每次接待活动结束后 | `exp-{year}-session-{seq:02d}` |
| `monthly/` | monthly | 每月定期 | `exp-{year}-monthly-{seq:02d}` |
| `lesson/` | lesson | 人工主动触发 | `exp-{year}-lesson-{seq:02d}` |

序号 `{seq}` 在每个 subtype 内独立计数，从 01 开始，按 event_date 升序排列。

---

## Frontmatter 模板

```yaml
---
title: <事件标题>
type: experience
entity_id: exp-{year}-{subtype_abbr}-{seq:02d}
subtype: session | monthly | lesson
event_date: YYYY-MM-DD
status: active
created: YYYY-MM-DD
updated: YYYY-MM-DD

dimensions:
  # 由 domain-config.xlsx Experience Types Sheet 定义，按行业配置
  # 展厅行业示例：
  theme_packages: []        # 本次使用的主题包
  module_ids: []            # 涉及的功能模块 ID
  client_tier: ""           # 客户层级
  attendee_count: 0         # 接待人数

subject:
  - clients/某客户实体.md
  - modules/某功能模块.md

exhibited_assets:
  - type: video
    label: ""
    path: sources/media/

sources:
  - sources/reports/YYYY-MM-DD-报告文件名.pdf
---
```

---

## 跨实体增益说明

`session` 类型的 experience 实体摄入后，会自动触发对 `subject` 关联实体的增益：

- **增益 A**：`[qa-record]` → 关联模块的 `[qa]` 分区（追加真实问答）
- **增益 B**：`[narration-record]` → 关联模块的 `[narration]` 分区（追加实际话术）
- **增益 C**：`[visitor-insights]` → `wiki/schema-suggestions.md`（scenarios 标签建议）
- **增益 D**：客户关注点数据 → 关联客户实体的 `preference_notes`（追加偏好记录）

增益行为受 `wiki/config.yml` 中 `experience.auto_enrich` 控制。

---

## 生命周期规则

| 状态 | 触发条件 |
|------|---------|
| `active` | 默认状态 |
| `outdated` | Lint 检测到关联 subject 实体已 archived，或 event_date 超过时效阈值 |
| `archived` | 系统或内容环境发生重大变更，历史记录失去参考价值 |

experience 实体不强制归档，其历史价值高于时效性。
