# SCHEMA-CORE — 通用核心规则

本文件是 company-wiki 知识库系统的**通用规则层**，与任何行业领域、任何下游应用均无关。  
行业枚举、字段清单、关联关系等**领域配置**均存放在 `schema/domain-config.xlsx`。

> 上一版本：`SCHEMA.md`（v0.1，硬编码展厅行业）→ v1.0 重构为本文件 + domain-config.xlsx  
> 当前版本：v1.1，新增资产引用、场景标签、正文分区约定，§三改为下游扩展协议

---

## 一、目录结构规范

```
sources/                    # 原始材料（只读，不修改，不进 git）
  proposals/                # 己方历史方案（支持子文件夹分类）
  competitors/              # 友商方案（竞品情报）
  patents/                  # 发明专利文件
  certificates/             # 资质证书文件
  policies/                 # 行业政策文件
  media/                    # 多媒体资产（视频、图片、HTML、PPT 等，按需创建子目录）
  annotations/              # 人工补充材料（讲解词、问答对、陪练脚本等，可选）

schema/                     # Schema 定义层（进 git）
  SCHEMA-CORE.md            # 本文件：通用规则
  domain-config.xlsx        # 领域配置：企业自定义枚举和字段

wiki/                       # LLM 生成和维护的知识库（进 git）
  <实体类目录>/              # 由 domain-config.xlsx Sheet1 定义
  clients/                  # 客户案例（脱敏，始终存在）
  credentials/              # 证书与专利（始终存在）
    patents/
    certificates/
    credentials-index.md
  policies/                 # 政策依据（含有效期）
  competitors/              # 竞品画像（始终存在）
  archive/                  # 已归档知识（不参与 Query）
  index.md                  # 内容目录（分类索引）
  log.md                    # 操作日志（只追加，不修改历史）

prompts/                    # 标准操作提示词模板
```

---

## 二、Wiki 页面格式规范

### 2.1 标准 Frontmatter

每个 wiki 页面必须包含以下元数据头：

```yaml
---
title: 页面标题
type: <类型，由 domain-config.xlsx Sheet1 定义>
tags: [标签1, 标签2]
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: active | outdated | archived

# ── 通用身份字段 ───────────────────────────
entity_id: <类型前缀>-<年份>-<行业缩写>-<地点缩写>-<序号>
# 示例：client-2024-telecom-guangzhou-01
version: v1
sources:
  - proposals/文件名.pdf   # 摄入来源，按版本追加，不覆盖

# ── v1.1 新增：资产引用 ───────────────────
# 可选。下游应用从此字段获取可直接使用的文件/链接。
# 与 sources 的区别：sources 是摄入溯源，assets 是可交付的资产引用。
assets:
  - type: video            # video | image | html | ppt | pdf | excel | link
    label: 资产名称          # 供人工和 LLM 识别
    path: sources/media/文件名.mp4    # 本地路径（可选）
    url: https://...                  # 远程 URL（可选，path 和 url 至少提供一个）
    description: 一句话描述该资产的内容和适用场合

# ── v1.1 新增：场景标签 ───────────────────
# 可选。标注该实体适用的下游场景，供下游应用快速过滤。
# 枚举值由 domain-config.xlsx Sheet2 的 scenarios 列定义，可自由扩展。
scenarios: [场景A, 场景B]
# 示例：[方案生产, AI策展, 智能问答, AI陪练]
---
```

- `status: outdated` — 内容可能过时，Query 时降权提示，不自动排除
- `status: archived` — 已确认过时，移入 `wiki/archive/`，**不参与任何 Query**
- `assets` 和 `scenarios` 均为可选字段，没有则省略，不填空数组
- 每次修改必须更新 `updated` 字段

### 2.2 正文分区约定（可选）

wiki 页面正文可包含若干**类型化分区**，格式为带类型标签的二级标题：

```markdown
## [summary] 内容摘要
（LLM 摄入时生成的结构化摘要，通用，所有下游场景均可消费）

## [narration] 讲解词
（人工整理的演讲/导览词，适合 AI 策展、数字人场景）

## [qa] 问答对
（结构化 Q&A，适合智能问答场景）
Q: ...
A: ...

## [training] 陪练脚本
（角色扮演或话术训练脚本，适合 AI 陪练场景）
```

**约定规则：**
- 类型标签小写，放在 `##` 标题最前方的方括号内
- 下游应用按需扫描特定类型的分区，忽略不需要的分区
- 所有分区均为可选，缺失不影响其他分区和 Frontmatter 的有效性
- 类型标签枚举不做硬约束，可按业务需要自由扩展
- 人工补充的分区来源文件统一放入 `sources/annotations/`，Ingest 时按需写入

---

### 2.3 Version History 块（可选）

当页面经历过版本更新时，在 frontmatter 后追加：

```yaml
history:
  v1:
    updated_at: YYYY-MM-DD
    changed_fields:
      - field_name: 旧值（来自 sources/旧文件名.pdf）
  v2:
    updated_at: YYYY-MM-DD
    changed_fields:
      - field_name: 旧值（来自 sources/新文件名.pdf）
```

### 2.4 entity_id 命名规则

```
格式：{type_prefix}-{year}-{industry_abbr}-{city_abbr}-{seq:02d}

示例：
  client-2024-telecom-guangzhou-01   # 2024年广州电信客户案例，第1份
  policy-2023-energy-national-01     # 2023年能源行业全国性政策，第1条
  competitor-huawei-ent-01           # 华为企业展厅竞品，第1份情报
```

- `type_prefix` 取自 domain-config.xlsx Sheet1 的"ID前缀"列
- 同一项目不同版本**共用同一 entity_id**，通过 version 区分
- 一旦分配不得修改，即使页面 archived 后仍保留

---

## 三、下游扩展协议

### 3.1 设计原则

**wiki 是纯粹的知识输出层，不感知任何下游应用的存在。**

- wiki 只负责：结构化存储知识、维护版本和生命周期、输出标准格式的 Frontmatter + 正文
- 下游应用只负责：定义自己的过滤逻辑、消费所需的字段和分区、不向 wiki 层写入任何约束
- 两者之间的唯一契约：本 SCHEMA-CORE.md 定义的字段格式和分区约定

这意味着：新增一个下游应用，**不需要修改 wiki 任何文件**；wiki 字段新增或变更，下游应用在自己的节奏内适配。

### 3.2 下游应用接入契约

任何下游应用在接入 wiki 时，应自行定义：

| 决策点 | 说明 | 示例 |
|--------|------|------|
| **加载哪些目录** | 根据应用场景选择 wiki/ 子目录 | 策展应用只加载 `exhibits/`；方案应用加载多个目录 |
| **按哪些字段过滤** | 从 Frontmatter 字段中选择过滤维度 | 按 `scenarios`、`industry`、`type`、`status` 过滤 |
| **消费哪些正文分区** | 按 `[type]` 标签提取所需分区 | 问答应用提取 `[qa]` 分区；策展应用提取 `[narration]` |
| **如何处理资产** | 从 `assets` 字段获取文件路径或 URL | 策展应用读取 `assets[].url` 组装播放序列 |
| **生命周期过滤** | 必须遵守：`archived` 不参与；`outdated` 可降权 | 所有下游应用均须实现此规则 |

### 3.3 生命周期过滤（所有下游必须实现）

无论何种下游应用，以下规则不可绕过：

- `status: archived` — **完全排除**，不得出现在任何应用的上下文中
- `status: outdated` — 可使用，但必须向用户标注该内容存在过期风险

### 3.4 wiki 层变更通知规则

当 SCHEMA-CORE.md 或 domain-config.xlsx 发生变更时，在 `wiki/log.md` 记录变更摘要（操作类型：`SCHEMA-UPDATE`），供各下游应用团队参考适配，无需逐一同步。

---

## 四、版本管控规则（Ingest 时执行）

### 4.1 五步流程

```
步骤 0：读取 schema/domain-config.xlsx，确认本次 Ingest 的提取字段清单

步骤 1：解析文件元数据
  - 提取：项目名 / 客户名 / 地点 / 日期 / 版本信号词（如"概念版"、"投标版"、"最终版"）

步骤 2：搜索现有 wiki 实体
  - 在 wiki/ 中按 entity_id 或 title 匹配是否存在同项目页面
  - 匹配优先级：entity_id 精确匹配 > title 模糊匹配（项目名+客户名）

步骤 3a（不存在）：新建页面
  - 生成 entity_id（规则见 §2.3）
  - 写入完整 frontmatter：version: v1，status: active
  - sources 字段填入当前文件名

步骤 3b（已存在）：版本比对与更新
  - 逐字段对比新旧值
  - 有差异的字段：新值写入正文，旧值移入 history: 块（标注来源文件）
  - 无差异的字段：保持不变
  - sources 列表追加当前文件名（不覆盖）

步骤 4：更新版本元数据
  - version 递增（v1 → v2 → v3 ...）
  - updated_at 更新为当前日期
```

### 4.2 版本比对示例

```yaml
---
entity_id: client-2024-telecom-guangzhou-01
version: v3
status: active
updated: 2024-11-20
sources:
  - proposals/2024-广州移动展厅-概念方案.pdf   # v1
  - proposals/2024-广州移动展厅-投标方案.pdf   # v2
  - proposals/2024-广州移动展厅-最终方案.pdf   # v3（当前）
---

history:
  v1:
    updated_at: 2024-03-10
    changed_fields:
      - budget_range: 500-800万（来自概念方案）
  v2:
    updated_at: 2024-07-15
    changed_fields:
      - budget_range: 800-1000万（来自投标方案）
      - proposal_stage: 规划方案（来自概念方案）
```

---

## 五、三态生命周期规则

### 5.1 状态定义

| 状态 | 含义 | Query 行为 | 存放位置 |
|------|------|-----------|----------|
| `active` | 当前有效 | 正常参与 | wiki/ 原位 |
| `outdated` | 疑似过期 | 参与，但加 ⚠️ 前缀警告 | wiki/ 原位，加标注 |
| `archived` | 已退出 | **不参与** | `wiki/archive/`（原路径镜像）|

### 5.2 自动触发条件（Lint 检测）

| 实体类型 | 触发条件 | 目标状态 |
|----------|----------|----------|
| 政策文件 | 超过 `valid_until` 日期 | `outdated` |
| 证书 | 距到期不足 90 天 | `outdated` |
| 证书 | 已过到期日 | `archived` |
| 客户案例（方案）| 被同项目更新版本完全覆盖 | `archived` |
| 其他 | 手动确认 | 任意 |

### 5.3 归档操作规范

将页面移入 `wiki/archive/` 时，在原 frontmatter 后追加：

```yaml
archived_at: YYYY-MM-DD
archive_reason: 政策文件已到期，由《xxx新政策》替代
superseded_by: policies/xxx-new-policy.md   # 可选，指向替代页面
```

`wiki/archive/` 目录结构镜像原路径，例如：
```
wiki/archive/
  policies/
    2022-行业标准-旧版.md
  credentials/certificates/
    资质证书-A-expired.md
```

---

## 六、知识沉淀规则

- **中标方案**的框架优先级高于未中标方案，提取时标注
- **友商方案**只流向 `wiki/competitors/`，不污染己方模板
- **客户信息**写入 wiki 前必须脱敏（用"某地市电信"代替具体名称）
- **过时内容**不直接删除，先标记 `status: archived`，移入 `wiki/archive/`
- 每次 Query 生成的有价值洞察必须回写 wiki（不允许只在对话中消耗）

---

## 七、操作规则摘要（详见 prompts/）

| 操作 | 提示词文件 | 核心用途 |
|------|-----------|---------|
| Ingest | `prompts/ingest.md` | 摄入新材料，含版本管控 |
| Ingest Experience | `prompts/ingest-experience.md` | 摄入事件报告，触发跨实体增益（v2.1） |
| Query | `prompts/query.md` | 为新方案生产提供素材，含对话式反馈捕获 |
| Lint | `prompts/lint.md` | 生命周期检测与归档建议 |
| Validate | `prompts/validate.md` | Obsidian Canvas 可视化验证 |

---

## 八、Obsidian 集成规范

- Vault 根目录：整个 `company-wiki/` 目录
- **内部引用必须使用 wikilink 格式**：`[[industries/通信行业]]`，禁止 Markdown 链接
- 推荐插件：Dataview（必装）、Graph Analysis（可选）
- Dashboard：`wiki/_dashboard.md`
- Canvas 规范：见原 SCHEMA.md §七（v0.1 验证工具，v1.0 起不参与 Query 路径）

---

## 九、log.md 日志格式

```
[YYYY-MM-DD HH:MM] {操作类型} | {文件/路径} | {说明}
```

| 操作类型 | 含义 |
|---------|------|
| INIT | 系统初始化 |
| INGEST | 摄入新材料 |
| VERSION-UPDATE | 版本覆盖更新 |
| ARCHIVE | 知识归档 |
| QUERY | 执行查询（可选记录） |
| LINT | 健康检查 |
| FEEDBACK | 对话式反馈反哺（v2.1 Path B）|
| SYNC-CHECK | 双路径同步评估记录 |
| EXPERIENCE-INGEST | 摄入经验事件报告（v2.1）|
| EXPERIENCE-ENRICH | 跨实体增益执行记录（v2.1）|
| SCHEMA-UPDATE | Schema 或领域配置变更记录 |

---

## 十、experience 实体规范（v2.1）

### 10.1 实体定位

`experience` 是**动态事件型**实体，与现有静态描述型实体（`client`/`module` 等）的核心区别：

| 维度 | 静态描述型（如 client/module） | 动态事件型（experience） |
|------|-------------------------------|------------------------|
| 记录内容 | 某事物**是什么** | 某件事**发生了什么** |
| 时间属性 | 无强时间绑定 | 必须有 `event_date` |
| 来源 | 方案文档、资料文件 | 活动报告、运营记录 |
| 增值机制 | 版本管控覆盖更新 | 跨实体增益反哺关联实体 |

存放目录：`wiki/experiences/{subtype}/`，目录说明见 `wiki/experiences/README.md`。

### 10.2 experience Frontmatter 规范

```yaml
---
title: <事件标题，建议格式："YYYY-MM-DD [客户/主题] [subtype中文名]">
type: experience
entity_id: exp-{event_year}-{subtype_abbr}-{seq:02d}
subtype: <来自 domain-config.xlsx Experience Types Sheet 的 subtype_abbr>
event_date: YYYY-MM-DD
status: active
created: YYYY-MM-DD
updated: YYYY-MM-DD

# 事件维度（由 domain-config.xlsx Experience Types Sheet 的 coreDimensions 定义）
dimensions:
  {key}: {value}    # 各行业自行在 domain-config 中定义维度字段名

# 本次事件涉及的 wiki 实体
subject:
  - clients/某客户实体.md
  - modules/某功能模块.md

# 本次活动中实际使用的资产（字段名可在 domain-config 中自定义）
exhibited_assets:
  - type: video
    label: 资产名称
    path: sources/media/文件名.mp4

sources:
  - sources/reports/YYYY-MM-DD-报告文件名.pdf
---
```

### 10.3 entity_id 规则

```
格式：exp-{event_year}-{subtype_abbr}-{seq:02d}

示例：
  exp-2026-session-01    # 2026年第1份接待活动报告
  exp-2026-monthly-03    # 2026年第3份运营月报
  exp-2026-lesson-01     # 2026年第1份经验沉淀
```

- `subtype_abbr` 取自 domain-config.xlsx Experience Types Sheet 的 `subtype_abbr` 列
- 序号在每个 subtype 内独立计数，从 01 开始，按 `event_date` 升序排列
- 一旦分配不得修改

### 10.4 跨实体增益规则

`experience` 实体摄入后触发的增益逻辑（详见 `prompts/ingest-experience.md` 步骤 5）：

| 增益类型 | 来源分区 | 写入目标 | 是否直接修改 |
|---------|---------|---------|------------|
| 增益 A | `[qa-record]` | 关联模块 `[qa]` 分区（追加） | 是，标注来源 |
| 增益 B | `[narration-record]` | 关联模块 `[narration]` 分区（追加） | 是，标注来源 |
| 增益 C | `[visitor-insights]` | `wiki/schema-suggestions.md` | 否，仅建议 |
| 增益 D | 客户关注点数据 | 关联客户 `preference_notes`（追加） | 是，标注来源 |

增益 A/B/D 均为追加操作，不覆盖已有内容；增益 C 写入 schema-suggestions.md 等待人工确认。
增益行为受 `wiki/config.yml` 中 `experience.auto_enrich` 控制。

### 10.5 experience 生命周期规则

| 状态 | 触发条件 |
|------|---------|
| `active` | 默认状态 |
| `outdated` | Lint 检测到关联核心 subject 实体已 archived，或 event_date 超过配置阈值 |
| `archived` | 系统或内容环境发生重大变更，历史记录失去参考价值 |

experience 实体**不强制归档**，历史价值高于时效性——旧的活动记录仍可作为历史样本使用。

### 10.6 best-expression 字段规范

`best-expression` 是通用可选字段，用于记录对特定受众的**最优表达方式**，由 Path B 对话捕获写入：

```yaml
best-expression:
  - audience: 政府客户
    prefer: "数字政务"
    avoid: "智慧城市"
    source: feedback-2026-04-20    # 来源记录（对话日期或 experience entity_id）
```

---

## 十一、wiki/config.yml 运行时配置规范（v2.1）

`wiki/config.yml` 是 wiki 运行时的行为配置文件，控制自动化程度。**所有开关默认关闭**，不影响现有手动工作流。

### 11.1 文件位置与作用域

- 路径：`wiki/config.yml`（进 git，可版本追踪）
- 作用域：所有 prompts 在执行前应读取此文件，以决定自动化行为

### 11.2 事件驱动摄入开关

```yaml
event_driven_ingest:
  enabled: false          # 主开关（默认关闭）
  watch_paths: [...]      # enabled=true 时扫描的目录
  trigger_mode: auto-confirm | auto-silent
  exclude_patterns: [...]
```

- `enabled: false`：所有 ingest-experience 均手动指定文件，不扫描目录
- `enabled: true`：执行 ingest-experience.md 时，自动扫描 watch_paths 中未摄入的文件
- `auto-confirm`（推荐）：列出待处理文件清单，用户确认后执行
- `auto-silent`：静默自动执行，完成后通知（谨慎使用）

### 11.3 增益行为配置

```yaml
experience:
  auto_enrich: true           # ingest-experience 后是否触发跨实体增益
  enrichment_confirm: true    # 增益前是否展示变更列表等待确认
```
