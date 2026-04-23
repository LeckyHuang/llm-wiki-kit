# llm-wiki-kit 演进路线图

> 本文档记录 llm-wiki-kit 知识库系统从初始框架到完整知识中台的分阶段演进计划。  
> 每个版本独立可交付，上一版本是下一版本的前提。  
> 最后更新：2026-04-22

---

## 愿景

构建一套**工具无关、领域可配置、应用解耦、自我进化**的企业级 LLM Wiki 知识基础设施：

- 企业提供原始材料（sources/）和领域配置（domain-config.xlsx），系统生长出对应的结构化知识库
- 知识库不只存储结构化事实，还索引多媒体资产、追踪知识时效、区分内外部来源
- **wiki 是纯粹的知识输出层，不绑定任何下游应用**——同一套知识库可同时驱动：方案生产、AI 策展、智能问答、AI 陪练等完全不同的 AI 应用场景
- 各下游应用通过标准的 Frontmatter 字段（`type`/`scenarios`/`assets`/`status`）自行定义消费逻辑，新增应用无需修改 wiki 层任何文件

### 普适性原则（核心约束）

**llm-wiki-kit 的持续生命力来自普适性**。每一个设计决策都必须回答：「换一个行业的 domain-config.xlsx，这个机制还能工作吗？」

这意味着：

- **SCHEMA-CORE.md 只定义机制，不定义业务语义**——实体类型、字段名称、枚举值、经验分类、事件维度，全部在 domain-config.xlsx 中由使用者定义
- **示例只是示例**——ROADMAP 中出现的"展厅"、"接待活动"、"方案阶段"等，是当前最熟悉的参考场景，不是系统边界
- **下游扩展不侵入知识层**——应用层适配（wiki-app、AI 策展、陪练系统）的特殊性只在应用层解决，永远不向 wiki 层写入任何绑定逻辑
- **每一个新版本在设计时，同步考虑至少两个不同行业的适用性验证**（展厅行业 + 另一参照领域），以防设计过度具体化

---

## 版本全景

| 版本 | 代号 | 核心主题 | 状态 |
|------|------|----------|------|
| v0.1 | Bootstrap | 框架初始化 + 首批方案入库 + wiki-app 生产部署 | ✅ 已完成 |
| v1.0 | Foundation | 通用化 + 版本管控 + 知识生命周期 | ✅ 已完成 |
| v1.1 | Decouple | 应用解耦 + 资产引用 + 场景标签 + 正文分区约定 | ✅ 已完成 |
| v2.0 | Intelligence | Schema 自进化：自发现字段 + 冲突澄清 | ✅ 已完成 |
| v2.1 | Experience | 经验知识体系：运营反哺 + 事件驱动摄入 + 跨实体增益 | ✅ 已完成（2026-04-23）|
| v2.5 | Scale | 规模化支撑：媒体资产深化 + 图谱路由 | 🔲 待启动 |
| v3.0 | Expansion | 外脑机制 + 自动触发 + 服务端流水线 | 🔲 待启动 |
| v4.0 | Production | 方案生产闭环（md→html→PPT）| ⏸ 暂缓，应用层决策 |

---

## v0.1 Bootstrap — 已完成

**交付物**
- 完整目录结构（sources/ + wiki/ + prompts/）
- SCHEMA.md（核心规则文件）
- 三大操作 prompt 模板（ingest / query / lint）
- 多工具入口（CLAUDE.md / AGENTS.md / .cursorrules）
- Git 仓库初始化并推送至 GitHub

**遗留问题**
- ~~wiki/ 内容全部为空，尚未执行第一批 Ingest~~ → 已完成首批 Ingest，47 份历史方案已入库
- Schema 目前为展厅行业专用，通用化改造留至 v1.0

**生产环境状态**（2026-04-15）
- wiki-app 已部署至服务器，正式进入试运行阶段
- 当前 wiki 体积：`clients/` 212K（47份方案）、`canvases/` 224K（仅用于前期可视化验证，不参与任何查询路径，后续不再维护）
- 两条并行 Query 路径均已就绪：AI 直接操作路径（`prompts/query.md`）+ Web 应用路径（`wiki-app/app.py`）

---

## v1.0 Foundation — 已完成

### 目标

将系统从"展厅专用"升级为"任意领域可配置"，同时建立知识的版本管控和生命周期机制，为后续大批量 Ingest 打好地基。

### 0. 双路径同步规则（新增，优先于其他子项）

**背景**：系统现存两条并行的 Query 路径，需明确各自职责并保持同步：

| 路径 | 入口 | 适用场景 | 过滤逻辑所在层 |
|------|------|----------|--------------|
| AI 直接操作 | `company-wiki/prompts/query.md` | Claude/Cursor 直接读写 wiki | Prompt 文字描述 |
| Web 应用 | `wiki-app/app.py` `/api/query` | 生产环境前端用户 | 后端代码硬过滤 |

**规则**：每次更新任一路径的查询逻辑（新增过滤维度、调整加载目录、修改输出格式），必须同步评估另一路径是否需要对应调整，并在 `wiki/log.md` 中记录。

**当前已实现的 app.py 硬过滤**（可标注为部分完成）：
- ✅ 行业维度：`INDUSTRY_MAP` 精准映射到子目录，未选则不加载
- ✅ 展厅类型：`HALL_MAP` 精准映射，未选则不加载
- ✅ 勾选控制：`competitors` / `policies` / `credentials` 按需加载
- ✅ `clients`（历史案例库）与 `credentials` 解耦，独立控制——`clients` 仅在勾选"资质证书/案例"时加载
- ✅ 随手问（`/api/chat`）不加载 `clients`，字符上限收紧至 `MAX_CHAT_WIKI_CHARS`（默认 40000）
- ✅ `status: archived` 页面不进入 Query 上下文（v1.0 实现）
- ✅ `status: outdated` 页面带 ⚠️ 提示后仍参与 Query（v1.0 实现）

**交付物**
- [x] 在 SCHEMA-CORE.md 中写入双路径同步规则
- [x] 更新 query.md prompt，补充"本 prompt 适用于 AI 直接操作路径"说明及与 wiki-app 的差异对照

---

### 1.1 通用化 Schema 设计

**问题**：当前 SCHEMA.md 硬编码了展厅行业的枚举值（行业类型、展厅类型等），其他企业无法直接复用。

**方案**：将 Schema 拆分为两层：

```
schema/
├── SCHEMA-CORE.md       # 通用规则（不变，与领域无关）
└── domain-config.xlsx   # 领域配置文件（企业自定义）
    - Sheet1: 实体类型定义
    - Sheet2: 字段清单（字段名 / 类型 / 是否必填 / 枚举值）
    - Sheet3: 关联关系定义（实体A → 关系 → 实体B）
```

`domain-config.xlsx` 由各企业自行填写，Ingest 时 LLM 读取它来决定提取哪些字段、如何分类。SCHEMA.md 保留为核心规则，但删除所有硬编码枚举，改为"参照 domain-config.xlsx"的引用式写法。

**交付物**
- [x] 重构 SCHEMA.md，删除硬编码枚举，改为引用 domain-config（保留为向后兼容入口）
- [x] 新建 `schema/SCHEMA-CORE.md`（通用规则，9个章节）
- [x] 新建 `schema/domain-config.xlsx`（4个Sheet：实体类型/字段清单/关联关系/预留v4章节结构，展厅行业示例已填）
- [x] 更新 ingest.md prompt，加入读取 domain-config 的步骤

---

### 1.2 知识版本管控

**问题**：同一项目可能先后出现"概念版→投标版→最终中标版"，重复 Ingest 会产生冗余或覆盖错误。

**方案**：Ingest 时增加"身份识别 + 版本比对"步骤：

```
Ingest 流程（新增步骤）：
1. 解析文件元数据（项目名/客户名/日期/版本号）
2. 在 wiki/ 中搜索是否存在同项目实体
3. 若不存在 → 新建（标注 version: v1, source: 文件名）
4. 若存在 → 执行版本比对：
   a. 逐字段比对新旧值
   b. 有差异的字段：新值写入正文，旧值移入 history: 块
   c. 无差异的字段：保持不变
5. 更新 version 号和 updated_at 时间戳
```

wiki 页面新增标准 frontmatter：

```yaml
---
entity_id: proj-2024-telecom-guangzhou-01
version: v3
status: active          # active / outdated / archived
created_at: 2024-03-10
updated_at: 2024-11-20
sources:
  - proposals/2024-广州移动展厅-概念方案.pdf   # v1
  - proposals/2024-广州移动展厅-投标方案.pdf   # v2
  - proposals/2024-广州移动展厅-最终方案.pdf   # v3（当前）
---
```

**交付物**
- [x] 更新 ingest.md prompt，加入身份识别和版本比对逻辑（5步流程）
- [x] 定义 wiki 页面 frontmatter 标准（entity_id / version / status / sources / history: 块）
- [x] 在 SCHEMA-CORE.md 中写入版本管控规则（§四）

---

### 1.3 知识生命周期与归档机制

**问题**：政策文件过期、证书失效、旧版方案被完全取代——这些知识需要退出但不能删除。

**方案**：三态生命周期模型：

```
active → outdated → archived
```

| 状态 | 含义 | 触发条件 | 存放位置 |
|------|------|----------|----------|
| active | 当前有效，参与 Query | 默认状态 | wiki/ 原位 |
| outdated | 疑似过期，Query 时降权提示 | Lint 检测 / 时间规则 / 被新版本覆盖 | wiki/ 原位，加标注 |
| archived | 已退出，不参与 Query | 用户在 Lint 报告中确认 | wiki/archive/（原路径镜像） |

归档规则（在 SCHEMA-CORE.md 中定义）：
- 政策文件：超过 `valid_until` 日期 → 自动标记 outdated
- 证书：距到期不足 90 天 → 标记 outdated，到期后 → archived
- 方案实体：被同项目更新版本完全覆盖 → archived
- 其他实体：用户手动确认

`wiki/archive/` 中每个文件保留原 frontmatter，新增：
```yaml
archived_at: 2025-06-01
archive_reason: 政策文件已到期，由《xxx新政策》替代
superseded_by: policies/xxx-new-policy.md   # 可选
```

**交付物**
- [x] 在 SCHEMA-CORE.md 中定义三态生命周期规则和归档触发条件（§五）
- [x] 创建 wiki/archive/ 目录结构（含 README.md 说明归档规范）
- [x] 更新 lint.md prompt，加入7类生命周期检测项和归档建议输出
- [x] 更新 query.md prompt，Query 时自动排除 archived，outdated 加 ⚠️ 警示

---

### v1.0 里程碑验收标准

- [ ] 可以用一份新的 domain-config.xlsx（非展厅行业）成功完成 Ingest，生成合理的 wiki 页面（待实测）
- [ ] 对同一项目执行两次 Ingest（不同版本），旧值正确保存在 history: 块（待实测）
- [ ] Lint 能识别过期政策并输出归档建议报告（待实测）

### 生产环境状态（2026-04-17）

- wiki-app 更新：`app.py` 加入 frontmatter 生命周期过滤（`_read_wiki_file`）、概算文件 PDF 预览端点
- 新增依赖：`python-frontmatter==1.1.0`
- schema/ 目录已建立，`SCHEMA-CORE.md` + `domain-config.xlsx` 就绪
- 现有 47 份方案**无需重新 Ingest**，与新 frontmatter 标准向后兼容

### 遗留说明

- ~~**Schema 通用性边界**：wiki-app 的目录名为硬编码，跨度过大的领域需改 app.py~~ → **已在 v1.1 通过下游扩展协议解决**，wiki 层不再感知任何下游应用
- **服务端 Ingest**：当前仍为本地操作，server-side Ingest pipeline 规划入 v3.0；阶段性方案见 ROADMAP v3.0 §3.3
- **旧页面 entity_id 补全**：现有客户案例页缺少 entity_id / version 字段，下次对该文件重新 Ingest 时顺手补充即可

---

## v1.1 Decouple — 已完成

### 目标

将 wiki 从"方案生产专用知识库"重新定位为**可驱动任意 AI 应用的知识基础设施**，通过最小改动实现架构级解耦。

### 核心变更

**SCHEMA-CORE.md 更新（v1.1）**

- **§二.1 Frontmatter 新增两个可选字段**：
  - `assets[]`：资产引用列表，每条含 `type / label / path / url / description`，供下游应用直接消费文件或链接（与 `sources` 的区别：`sources` 是摄入溯源，`assets` 是可交付的资产引用）
  - `scenarios[]`：场景标签，标注该实体适用的下游场景（如 `[方案生产, AI策展, 智能问答]`），供下游快速过滤

- **新增 §二.2 正文分区约定**：用 `## [type] 标题` 格式定义可选的类型化正文分区（`[summary]` / `[narration]` / `[qa]` / `[training]` 等），下游应用按需提取对应分区，互不干扰，类型可自由扩展

- **§三 从"双路径同步规则"改为"下游扩展协议"**：
  - wiki 不感知任何下游应用的存在
  - 新增下游应用无需修改 wiki 任何文件
  - 下游应用自行定义加载目录、过滤字段、消费分区、资产处理逻辑
  - 唯一强制约束：生命周期过滤（`archived` 完全排除，`outdated` 降权提示）

**目录补充**：`sources/media/`（多媒体原件）、`sources/annotations/`（人工补充材料，可选）

**prompts/ 更新**：`ingest.md` 和 `query.md` 去除 wiki-app 耦合引用；`query.md` 新增通用查询模板和 AI 策展配屏专用模板

### 对现有部署的影响

**wiki-app 零改动**——代码分析确认：`_read_wiki_file()` 只读 `status` 字段，新增的 `assets`/`scenarios` 以原始文本传入 LLM 上下文，不触发任何解析逻辑；新增的 `sources/media/` 和 `sources/annotations/` 目录在 `sources/` 下，`load_wiki()` 不会加载。

---

## v2.0 Intelligence — Schema 自进化：自发现字段 + 冲突澄清

### 目标

让系统的**知识结构**能够自我进化：Ingest 能主动发现 domain-config 未覆盖的有价值字段，对同一实体的矛盾描述能触发人工裁决，而不是静默覆盖。

> **与 v2.1 的分工**：v2.0 解决"wiki 的结构和 Schema 如何越来越准确"，v2.1 解决"wiki 的内容如何从运营中持续积累"。两者都是知识自进化，但来源和机制不同。

> **普适性说明**：自发现字段和冲突检测是通用机制，与行业无关。domain-config.xlsx 的进化方向由企业自己决定，系统只负责发现候选项并等待人工确认。

### 2.0.1 Ingest 自发现字段

**问题**：企业的 domain-config.xlsx 不可能穷举所有有价值的字段，大量隐性知识被遗漏。

**方案**：两阶段 Ingest：

```
阶段一：Schema 驱动提取（按 domain-config 逐字段提取，同 v1.0）

阶段二：自由发现扫描
  - LLM 重新扫描原文，寻找 Schema 未覆盖但高价值的内容
  - 提取后写入 wiki 页面的 auto_discovered: 块，加 [AUTO] 标注
  - 同时写入 wiki/schema-suggestions.md（Schema 进化建议池）
```

`schema-suggestions.md` 格式：
```markdown
## 待确认字段建议

| 建议字段名 | 发现来源 | 出现次数 | 示例值 | 建议加入 Schema? |
|-----------|---------|---------|-------|----------------|
| 竞标报价区间 | 3份投标方案 | 3 | 800-1200万 | ☐ |
| 主创团队规模 | 5份方案 | 5 | 12人 | ☐ |
```

用户定期审阅 schema-suggestions.md，勾选确认后，下次 Lint 时自动将这些字段正式化至 domain-config.xlsx。

**交付物**
- [x] 更新 ingest.md，加入两阶段 Ingest 逻辑
- [x] 定义 auto_discovered: 块的标准格式
- [x] 创建 wiki/schema-suggestions.md 模板和填写规范

---

### 2.0.2 冲突检测与澄清机制

**问题**：不同来源对同一实体的描述可能截然相反（如两份方案对某竞品的评价完全矛盾），直接覆盖会丢失信息，两者并存又造成混乱。

**方案**：Ingest 时加入冲突检测，输出澄清任务：

```
冲突类型及处理：

Type A - 数值冲突（同字段，不同来源，值不同）
  → 处理：两值并存，标注各自来源，加 [CONFLICT] 标记
  → 等待用户在下次 Lint 时裁决

Type B - 定性矛盾（对同一实体的描述方向相反）
  → 处理：暂停写入该字段，生成澄清任务
  → 澄清任务写入 wiki/pending-clarifications.md

Type C - 逻辑矛盾（A说X是优势，B说X是劣势）
  → 处理：两者均写入，加 [PERSPECTIVE: 来源名] 标注
  → 备注：观点差异，非事实冲突，无需强制统一
```

`pending-clarifications.md` 格式：
```markdown
## 待澄清项

### [CONFLICT-001] 竞品A的系统集成能力评级
- 来源1：proposals/xxx.pdf → 评级：强（"行业领先的集成能力"）
- 来源2：competitors/yyy.pdf → 评级：弱（"集成接口不开放"）
- 建议裁决：[ ] 以来源1为准  [ ] 以来源2为准  [ ] 两者均保留（注明背景差异）
```

**交付物**
- [x] 更新 ingest.md，加入冲突检测逻辑和三类冲突处理方式
- [x] 创建 wiki/pending-clarifications.md 模板
- [x] 更新 lint.md，将 pending-clarifications.md 纳入健康检查（检查项 7 冲突积压 + 检查项 8 Schema 建议积压）

---

### v2.0 里程碑验收标准

- [x] Ingest 一份新方案后，能在 `wiki/schema-suggestions.md` 中看到至少 3 条有价值的自发现字段建议
- [x] 对同一实体的矛盾描述，`wiki/pending-clarifications.md` 能正确捕获并分类呈现
- [ ] 用一份非展厅行业的 domain-config.xlsx 完成 Ingest，自发现字段机制同样生效（通用性验证，待实测）

---

## v2.1 Experience — 经验知识体系

### 目标

建立从**运营实践**到**知识库**的反哺回路，使 wiki 不再只是静态文档的结构化副本，而是随着真实使用持续自我增益的活体知识库。

v2.1 解决两类知识来源，这两类来源在**任何行业**都普遍存在：

| 来源类型 | 行业无关的通用描述 | 展厅行业参照示例 |
|---------|-----------------|--------------|
| **结构化事件报告** | 业务活动完成后生成的过程记录，涵盖执行维度、参与方、实际反馈 | 每次接待活动后的三份过程报告（拾音分析 + 展项数据） |
| **对话式知识捕获** | 日常操作中产生的即时修正、偏好反馈、知识补充 | 日常 query 时发现的说法纠偏、客户偏好更新 |

> **普适性说明**：展厅行业的"接待活动"对应法律行业的"案件结案回顾"、医疗行业的"术后复盘"、软件行业的"迭代回顾"。事件的维度和分区类型在 domain-config.xlsx 中配置，SCHEMA-CORE.md 只定义通用机制。

---

### 2.1.1 experience 实体类型

**新增 wiki 实体类型：`experience`**，存放于 `wiki/experiences/` 目录。

与现有实体类型的核心区别：
- `client` / `module` / `industry` 等是**静态描述型**——描述某事物是什么
- `experience` 是**动态事件型**——记录某件事发生了什么，带时间戳，有主观观察

**通用 Frontmatter 模板**：

```yaml
---
title: <事件标题>
type: experience
entity_id: exp-{year}-{event_type_abbr}-{seq:02d}
subtype: <来自 domain-config.xlsx Experience Sheet 的枚举>
event_date: YYYY-MM-DD
status: active
created: YYYY-MM-DD
updated: YYYY-MM-DD

# 事件维度（由 domain-config.xlsx 定义，非硬编码）
# 各行业自行在 domain-config 中定义本行业的事件维度名称
dimensions:
  dimension_1_key: value     # 例：exhibition hall → theme_packages: [AI体验主题]
  dimension_2_key: value     # 例：law firm → practice_area: 知识产权
  dimension_3_key: value

# 关联的 wiki 实体（本次事件涉及的实体）
subject:
  - clients/某客户实体.md
  - modules/某功能模块.md

# 资产引用（v2.1 新增：事件中实际使用的资产）
exhibited_assets:           # 字段名可在 domain-config 中自定义
  - type: video
    label: 某视频名称
    path: sources/media/某视频.mp4

sources:
  - reports/YYYY-MM-DD-事件报告.pdf
---
```

**entity_id 规则**：`exp-{year}-{subtype_abbr}-{seq:02d}`，其中 `subtype_abbr` 取自 domain-config.xlsx Experience Sheet 的缩写列。

---

### 2.1.2 domain-config.xlsx 扩展

v2.1 在 domain-config.xlsx 中新增两个配置 Sheet：

**Sheet：Experience Types（经验类型表）**

| 子类型名 | 缩写 | 触发条件 | 核心维度字段 | 适用分区类型 |
|---------|------|---------|------------|------------|
| 接待活动报告 | session | 每次接待结束后 | 专场类型/主题包/展项/客户层级 | visitor-insights / narration-record / qa-record |
| 运营月报 | monthly | 每月定期 | 统计周期/核心指标 | data-summary / trend-analysis |
| 经验沉淀 | lesson | 人工主动触发 | 适用场景/问题类型 | lesson / recommendation |

> 这是展厅行业的示例填法。其他行业替换行内容即可，机制不变。

**Sheet：Experience Section Types（经验分区类型表）**

| 分区标签 | 含义 | 来源机制 | 适用 subtype |
|---------|------|---------|------------|
| `[visitor-insights]` | 参与方的关注点与反应 | 拾音分析/人工记录 | session |
| `[narration-record]` | 实际执行的讲解/陈述内容 | 拾音分析/录音转写 | session |
| `[qa-record]` | 现场问答实录 | 拾音分析/人工记录 | session |
| `[data-summary]` | 数据汇总与指标 | 系统数据导出 | monthly |
| `[lesson]` | 经验总结与规律 | 人工沉淀 | lesson |
| `[recommendation]` | 行动建议 | 人工沉淀 | lesson |

> 分区标签是对 v1.1 正文分区约定的延伸扩展。v1.1 定义了 `[summary]` / `[narration]` / `[qa]` / `[training]`，v2.1 新增 experience 专用分区。所有分区类型均为开放枚举，可按业务需要在 domain-config 中自由扩展。

---

### 2.1.3 双路径摄入机制

**路径 A：结构化事件报告摄入（新增 prompts/ingest-experience.md）**

事件报告（如接待活动报告、月度运营报告）是机器或系统生成的结构化文件，摄入逻辑与普通方案文件不同：

```
Ingest Experience 流程：

步骤 0：读取 domain-config.xlsx Experience Sheet
  - 确认本报告对应的 subtype
  - 加载该 subtype 的维度字段清单和适用分区类型

步骤 1：提取事件 Frontmatter
  - event_date（事件发生时间，非文件创建时间）
  - 按 domain-config 定义的维度字段逐项提取
  - 关联 wiki 实体（subject 字段）：匹配报告中提及的现有 wiki 条目

步骤 2：提取正文分区
  - 按该 subtype 的适用分区类型提取对应内容
  - 每个分区内容要求：具体、可引用，不做主观评价

步骤 3：写入 wiki/experiences/{subtype}/
  - 新建 experience 实体页面
  - 写入 log.md（操作类型：EXPERIENCE-INGEST）

步骤 4：触发跨实体增益（见 §2.1.4）
```

**路径 B：对话式知识捕获（升级 prompts/query.md）**

在 query.md 末尾增加轻量反馈捕获环节。与路径 A 的区别是：这里捕获的是**对话过程中发现的偏差和修正**，而非系统报告。

Query 会话结束时，LLM 识别并汇总本次交互中出现的知识修正，提示用户确认：

```markdown
## 本次查询反馈捕获

以下内容在本次查询中产生了修正或补充，请确认处理方式：

1. [知识修正] 指向实体：modules/某功能模块.md
   原描述："统一管理平台"
   修正为："端到端自主可控"
   → [ ] 直接更新 wiki（写入 history 块）
   → [ ] 仅本次有效，不更新

2. [知识空白] wiki 中缺少"项目交付周期"字段
   本次对话中的参考值：标准项目 4–6 个月
   → [ ] 新增至对应 wiki 实体
   → [ ] 加入 schema-suggestions.md（等待 Schema 级确认）
   → [ ] 忽略

3. [表达偏好] 对政府客户的描述倾向
   本次修正方向：使用"数字政务"优于"智慧城市"
   → [ ] 写入对应实体的 best-expression 字段
   → [ ] 忽略
```

用户确认后，LLM 执行对应的 wiki 更新，在 log.md 中记录（操作类型：`FEEDBACK`）。

**交付物**
- [x] 新建 `prompts/ingest-experience.md`（6 步完整流程 + 跨实体增益 A/B/C/D）
- [x] 更新 `prompts/query.md`，加入路径 B 反馈捕获模块
- [x] 在 SCHEMA-CORE.md 中定义 `experience` 实体类型规范（§十）
- [x] 在 SCHEMA-CORE.md 中定义 `best-expression` 字段规范
- [x] 在 SCHEMA-CORE.md 中定义 `config.yml` 机制说明（§十一）
- [x] 更新 log.md 枚举，新增 `EXPERIENCE-INGEST` / `EXPERIENCE-ENRICH` / `FEEDBACK` 操作类型
- [x] 在 domain-config.xlsx 中新增 Experience Types Sheet 和 Experience Section Types Sheet（含展厅行业示例）
- [x] 创建 `wiki/experiences/` 目录结构（session/ / monthly/ / lesson/ + README.md）
- [x] 新建 `wiki/config.yml`（事件驱动摄入开关，默认关闭）
- [x] **服务端支持（提前自 v3.0）**：扩展 `wiki-app/ingest_engine.py` 支持 experience 摄入 + 跨实体增益写入；`wiki-app/app.py` 增加 `ingest_type` 参数；`wiki-app/static/ingest.html` 新增摄入类型选择器

---

### 2.1.4 跨实体增益机制

这是 v2.1 最核心的设计。**experience 实体不只是存档，它会主动反哺关联的 wiki 实体。**

摄入一份事件报告后，触发以下增益逻辑：

```
跨实体增益流程（ingest-experience.md 步骤 4）：

对每一个 subject 实体（如 modules/AI数字人讲解系统.md）：

  增益 A：[qa] 分区追加
    来源：报告中的 [qa-record] 分区
    规则：仅追加真实发生的问答，不覆盖已有条目
    标注：在每条 Q&A 后注明来源（exp entity_id + event_date）

  增益 B：[narration] 分区追加
    来源：报告中的 [narration-record] 分区
    规则：追加讲解员的实际话术（非规划话术）
    标注：注明来源 + 讲解员角色（不记名）

  增益 C：scenarios 标签更新
    来源：报告中的 [visitor-insights] 分区
    规则：若发现该实体在新场景下产生显著反应，建议追加 scenarios 标签
    方式：写入 schema-suggestions.md 等待人工确认，不自动修改

  增益 D：client 实体偏好更新
    来源：报告中的客户关注点、兴趣点数据
    规则：在 clients/ 对应实体追加 preference_notes 段落（如已存在则追加，不覆盖）
    标注：注明来源 event_date 和接待场次

更新 experience 实体自身的 subject 字段，确认双向关联已建立。
```

> 这个机制使得同一个模块实体（如`modules/AI数字人讲解系统.md`）的 `[qa]` 和 `[narration]` 分区随着每次运营自动变得更丰富，无需人工干预。经过若干次接待后，该模块页面中沉淀的真实问答，质量将远超初始摄入时的"规划内容"。

---

### 2.1.5 experience 知识的生命周期

experience 实体使用与其他实体相同的三态生命周期（active / outdated / archived），但触发条件不同：

| 状态 | 触发条件 |
|------|---------|
| `active` | 默认状态，内容准确反映当时实际情况 |
| `outdated` | Lint 检测到关联的核心 subject 实体已 archived，或 event_date 超过配置的时效阈值 |
| `archived` | 系统或内容环境已发生重大变更，该历史记录失去参考价值 |

experience 实体不强制归档，其历史价值高于时效性——旧的接待记录依然可以作为"历史样本"供图谱分析使用（v2.5 接入）。

---

### v2.1 里程碑验收标准

> 开发已完成（2026-04-23），以下为功能验收项，待首批真实事件报告入库后确认。

- [ ] 完成一份事件报告的 ingest-experience 流程（Claude Code 路径），`wiki/experiences/` 中出现新实体
- [ ] wiki-app 服务端上传接待报告，选择"经验报告"类型，SSE 流式摄入完成并写入 wiki
- [ ] 跨实体增益触发：对应 modules/ 实体的 `[qa]` 分区新增来自报告的真实问答
- [ ] 对话式捕获触发：完成一次 query 并通过反馈捕获成功更新 wiki 中至少 1 个字段
- [ ] 用不同行业的 domain-config（替换 Experience Types Sheet）完成一次 experience 摄入，验证普适性

---

## v2.5 Scale — 规模化支撑：媒体资产深化 + 图谱路由

### 目标

当 wiki 规模从"个人/小团队使用"扩展到"客户侧多人运营"时，两类问题同时浮现：**媒体资产难以跨实体检索**、**全量扫描 token 线性膨胀**。v2.5 同时解决这两个规模化问题。

> **为何合并到同一版本**：两个问题的触发条件高度重合（wiki 规模增大），且媒体资产索引本身就是图谱路由的重要节点类型——合并处理比分版本做更连贯。

> **为何从 v3.0 提前到 v2.5**：原计划将媒体资产深化放在 v3.0，但对于媒体文件密集的客户场景（如展厅运营），资产索引是 Day-1 需求，不是"扩展功能"。v2.1 的 `exhibited_assets` 字段已预留接口，v2.5 将其正式建立成可查询的索引层。

> **普适性说明**：媒体资产索引和图谱路由是与行业完全无关的基础设施。asset type 枚举（video / image / html / ppt / pdf / excel / link / diagram）可在 domain-config.xlsx 中扩展；图谱路由的节点和关系类型由 wiki 实际内容决定，不需要额外配置。

---

### 2.5.1 媒体资产索引

> **基础层回顾**：v1.1 已在 SCHEMA-CORE.md 中定义了 `assets[]` frontmatter 字段（含 type / label / path / url / description），`sources/media/` 目录已建立。v2.1 新增了 `exhibited_assets` 字段记录事件中实际使用的资产。**v2.5 在此基础上建立跨实体的聚合索引层。**

**问题**：随着资产数量增长（数十到数百个），"找所有 video 类型的资产"、"找哪个展项用了哪个视频"这类查询，逐页读 Frontmatter 效率极低。

**方案**：建立全库资产聚合索引，由 Lint 自动维护：

```
wiki/assets/
  index.md          # 全库资产聚合索引（Lint 自动生成和更新）
  README.md         # 索引规范说明
```

`wiki/assets/index.md` 格式：

```markdown
# 资产索引

> 由 Lint 自动生成，最后更新：YYYY-MM-DD
> 来源：扫描所有 wiki 实体的 assets[] 和 exhibited_assets[] 字段

## 按类型检索

### video
| 资产标签 | 所属实体 | 文件/URL | 描述 |
|---------|---------|---------|------|
| 5G融合展示视频 | modules/场景演示大师 | sources/media/5g-demo.mp4 | 3分钟，适合省级客户 |
| ... | | | |

### html
| ... |

## 按实体检索

### modules/AI数字人讲解系统
- [video] AI数字人演示 → sources/media/digital-human-demo.mp4
- [ppt] 技术架构说明 → sources/media/dh-architecture.pptx

## 跨事件资产使用记录（来自 experience 实体）

| 资产标签 | 被引用次数 | 最近引用事件 |
|---------|---------|------------|
| 5G融合展示视频 | 7 | exp-2026-session-14 |
```

这个跨事件使用记录（来自 v2.1 的 `exhibited_assets`）本身就是高价值运营数据：高频使用的资产说明其内容强，低频说明可能需要更新或下线。

**交付物**
- [ ] 定义 `wiki/assets/index.md` 完整格式规范，写入 SCHEMA-CORE.md
- [ ] 更新 `prompts/lint.md`，加入资产索引自动聚合步骤（扫描 `assets[]` 和 `exhibited_assets[]`）
- [ ] 在 domain-config.xlsx Sheet2 中完善 `assets.type` 枚举值
- [ ] 更新 `prompts/query.md`，支持按资产类型跨实体检索（如"找所有包含 video 资产的模块"）

---

### 2.5.2 知识图谱路由（Graphify 集成）

**问题**：随着 wiki 实体增长（客户场景预期 150–300 页），Query 时全量扫描 wiki 的 token 消耗线性膨胀，超出实用阈值。

**触发阈值（调整后）**：

原 ROADMAP 设定的触发条件为"clients/ 超过 400K"，适用于内部场景。**客户侧运营规模更大，提前触发条件为以下任一：**
- `wiki/` 实体总数超过 **150 页**（含 experience 实体）
- 单次 Query 响应频繁出现 `[内容已截断]` 提示
- `wiki/experiences/` 中积累超过 **30 个** session 事件（图谱关联关系密度开始有意义）

**工具**：[Graphify](https://github.com/safishamsi/graphify)——将 Markdown 文件转化为知识图谱（NetworkX），Leiden 社区发现算法聚类，无需向量数据库，查询时 token 消耗最高可降低 71.5 倍。

**初始建图**：

```bash
/graphify ./wiki --mode deep
```

输出：
```
wiki/graph/
  graph.json        # 持久化图谱数据（进 git）
  graph.html        # 可交互可视化（进 git）
  GRAPH_REPORT.md   # 一页式关系摘要（进 git）
```

生成的关系示例（展厅行业）：
```
[通信运营商行业]  --常用展厅类型-->  [数智体验中心]         EXTRACTED 1.0
[数智体验中心]   --核心模块-->       [AI数字人讲解系统]     INFERRED  0.87
[AI数字人讲解系统] --在接待中使用-->  [exp-2026-session-12]  EXTRACTED 1.0  ← v2.1 新增节点
[广州电信展示中心] --偏好主题-->      [AI体验主题包]         INFERRED  0.73
```

注意：v2.1 新增的 `experience` 实体会成为图谱中的事件节点，连接 client 实体、module 实体和 asset 实体，形成"运营历史图谱"。

**图谱路由 Query 流程**：

```
原 Query 流程：接收参数 → 全量扫描 wiki → LLM 合成输出

新 Query 流程（图谱路由）：
  接收查询参数
    ↓
  /graphify query "{关键词}"   ← 图谱层快速定位相关节点（ms级）
    ↓
  取出相关节点对应的 wiki 页面列表（精准子集，通常 10–30 页）
    ↓
  仅将该子集内容喂给 LLM 合成输出（token 消耗大幅下降）
```

**AMBIGUOUS 关系 → 打通冲突澄清机制**：

Graphify 标记为 `AMBIGUOUS` 的关系自动追加写入 `wiki/pending-clarifications.md`（v2.0 已建立）：

```markdown
### [CONFLICT-G001] 图谱关系待澄清（来自 Graphify）
- 实体A：modules/场景演示大师.md
- 实体B：modules/AI内容生产工具-场景演示大师.md
- 疑似关系：重复实体 vs 包含关系（两者是同一事物吗？）
- 置信度：0.38（AMBIGUOUS）
- 建议裁决：[ ] 合并为同一实体  [ ] 保留，明确区分  [ ] 无关联
```

**Ingest 后自动刷新图谱**：

每次 Ingest（包括 ingest-experience.md）完成后追加执行：

```bash
/graphify ./wiki --update    # 仅处理变更文件（SHA256 缓存，成本极低）
```

**交付物**
- [ ] 安装 Graphify skill（`graphify claude install`）
- [ ] 首次在 `wiki/` 上运行 `/graphify . --mode deep`，生成初始图谱三文件
- [ ] 更新 `prompts/query.md`，加入图谱路由前置步骤
- [ ] 更新 `prompts/lint.md`，加入读取 `AMBIGUOUS` 关系并写入 `pending-clarifications.md` 的步骤
- [ ] 更新 `prompts/ingest.md` 和 `prompts/ingest-experience.md`，末尾加入 `/graphify --update` 步骤
- [ ] 在 SCHEMA-CORE.md 中记录图谱路由的 Query 两阶段流程规范
- [ ] 在 `graph.json` schema 中预留 `source_type: internal/external` 字段（为 v3.0 外脑机制预埋）

---

### v2.5 里程碑验收标准

- [ ] `/graphify . --mode deep` 在 `wiki/` 上成功运行，`graph.html` 可在浏览器中交互浏览
- [ ] `experience` 实体作为事件节点出现在图谱中，与 client/module/asset 节点正确关联
- [ ] `AMBIGUOUS` 关系自动出现在 `pending-clarifications.md` 中
- [ ] Query 通过图谱路由，实际喂入 LLM 的 wiki 内容子集明显小于全量
- [ ] `wiki/assets/index.md` 由 Lint 自动生成并反映全库媒体资产状态
- [ ] Ingest 新文件后 `--update`，图谱中出现对应新节点和关系

### v2.5 提前触发条件

无需等待 v2.0 / v2.1 全部完成，以下任一条件满足时应优先启动：
- `wiki/` 实体总数超过 150 页
- 单次 Query 频繁出现 `[内容已截断]`
- `wiki/experiences/` 积累超过 30 个 session 事件

---

## v3.0 Expansion — 外脑机制 + 自动触发 + 服务端流水线

### 目标

扩展知识库的"感知边界"和"运行自主性"：向外接入互联网知识补充（外脑），向下实现变更自动触发，向运维侧提供服务端 Ingest 流水线。

> **与 v2.0–v2.5 的分工**：v2.x 系列是知识库的"智能化"——知识结构自进化、经验自积累、规模自适应。v3.0 是知识库的"自动化"——减少人工触发、接入外部世界、降低运维成本。

> **普适性说明**：外脑机制（world-sources）和自动触发（config.yml）是通用基础设施。外部知识的来源类型（行业报告、竞品官网、政策文件等）可在 domain-config.xlsx 中扩展，不硬编码。

---

### 3.1 外脑机制（World Sources）

**问题**：内部知识库只反映企业自身经验，缺乏行业趋势、竞品动态、政策解读等外部视角。

**方案**：构建与内部 wiki 并行的外部知识空间：

```
world-sources/             # 外部原始材料（不进 git，同 sources/）
  industry-reports/        # 行业研究报告
  competitor-web/          # 竞品官网/公开材料
  policy-official/         # 政府政策原文
  news-articles/           # 行业新闻

wiki/external/             # 外部知识提炼（进 git，有明确标注）
  index.md
  industry-trends/
  competitors/             # 与 wiki/competitors/ 互补
  policies/                # 与 wiki/policies/ 互补
```

**核心设计原则**：
- 每个外部 wiki 页面顶部必须有 `[EXTERNAL]` 醒目标注
- 每条知识点标注 `source_url` + `crawled_at` 时间戳
- 外部知识按实体绑定：Ingest 内部方案提取出某竞品实体后，可触发外部搜索补充公开信息
- Lint 检查时，`crawled_at` 超过 180 天的外部条目标记"建议刷新"

**Query 筛选控制**：默认仅内部 wiki 参与检索；`--include-external` 同时召回，结果标注来源。

**交付物**
- [ ] 在 SCHEMA-CORE.md 中写入外部知识规范（标注要求、溯源规则、生命周期）
- [ ] 创建 `world-sources/` 和 `wiki/external/` 目录结构
- [ ] 新增 `prompts/ingest-external.md`（外部知识专用 Ingest prompt）
- [ ] 更新 `prompts/query.md`，加入 internal/external 筛选控制
- [ ] 更新 `prompts/lint.md`，加入外部知识时效检测

---

### 3.2 自动触发机制

**问题**：sources/ 更新频繁时，手动触发 Ingest 效率低，容易遗漏。

**方案**：通过 `wiki/config.yml` 配置触发模式：

```yaml
# wiki/config.yml

ingest:
  trigger_mode: manual          # manual / auto-confirm / auto-silent
  watch_paths:
    - sources/proposals/
    - sources/competitors/
    - sources/reports/          # v2.1 新增：事件报告目录
  exclude_patterns:
    - "*.tmp"
    - "~$*"

experience:
  auto_enrich: true             # Ingest experience 后是否自动触发跨实体增益
  enrichment_confirm: true      # true = 每次增益前等待人工确认，false = 静默执行

lint:
  schedule: monthly
  auto_archive: false

graph:
  auto_update: true             # v2.5 预留：Ingest 后是否自动执行 /graphify --update
```

触发模式：
- `manual`：完全手动（默认，适合初期）
- `auto-confirm`：检测到新文件时提示用户确认再执行（推荐日常）
- `auto-silent`：静默自动执行，完成后通知（适合批量场景，谨慎使用）

**交付物**
- [x] 创建 `wiki/config.yml` 及说明文档（已在 v2.1 提前实现）
- [x] 更新 SCHEMA-CORE.md，说明 config.yml 的作用和触发逻辑（已在 v2.1 提前实现）

---

### 3.3 服务端 Ingest 流水线

**背景**：当前所有 Ingest 均为本地操作（在 Claude Code / Cursor 中手动执行 prompt）。随着客户侧运营规模扩大，需要支持服务端批量处理。

> **v2.1 已提前实现阶段二（experience 类型）**：`wiki-app/ingest_engine.py` 已支持 experience 报告的服务端摄入 + 跨实体增益写入，`/api/admin/ingest/upload` 端点通过 `ingest_type=experience` 参数触发。标准文档的服务端批量处理（`ingest_batch.py`）仍规划于 v3.0。

**方案**：

```
服务端 Ingest Pipeline（阶段性方案）：

阶段一（v3.0 实现）：
  - 提供 CLI 脚本 tools/ingest_batch.py
  - 扫描 sources/ 中的新文件（与 wiki/log.md 比对，找出未 Ingest 的文件）
  - 批量调用 LLM API 执行 Ingest，写入 wiki/
  - 结果输出 ingest-report.md，供人工审核后合入 git

阶段二（已在 v2.1 完成，experience 类型）：
  - wiki-app /api/admin/ingest/upload 端点支持 ingest_type=experience
  - 上传报告文件 → LLM 流式摄入 → 写入 wiki/experiences/ + 跨实体增益
  - 支持 ingest_type=standard（原有）和 ingest_type=experience（v2.1 新增）
```

**交付物**
- [ ] 创建 `tools/ingest_batch.py`（CLI 批处理脚本，标准文档批量处理）
- [ ] 在 SCHEMA-CORE.md 中补充服务端 Ingest 与本地 Ingest 的一致性约束
- [ ] 更新 README.md，说明两种 Ingest 模式的适用场景

---

### v3.0 里程碑验收标准

- [ ] 触发一次外部补充，`wiki/external/` 中出现有溯源标注的外部知识页面
- [ ] Query 时 `--include-external` 能同时召回内外部知识且来源清晰区分
- [ ] `wiki/config.yml` 的 `auto-confirm` 模式在检测到新文件时正确提示
- [ ] `tools/ingest_batch.py` 能扫描出未 Ingest 文件并批量处理，输出审核报告

---

## v4.0 Production — 方案生产闭环（暂缓）

### 定位说明

v4.0 是**应用层能力**，不是知识基础设施层。wiki 系统在 v1.1 完成解耦后，方案生产应用可以独立开发，不需要等待 wiki 层达到 v4.0。

**暂缓原因**：

1. wiki 的核心价值是知识积累和检索，方案生产的最终形态（HTML/PPT 格式和品牌规范）是下游应用决策，不应由 wiki 层硬编码
2. md→HTML→PPT 工具链的选型（Marp / python-pptx / Remotion 等）需要在实际方案生产需求明确后再评估
3. wiki 知识库在 v2.x 达到足够的内容质量和结构化程度后，方案生产应用接入的价值才能充分体现

**预期时机**：在 v2.1 经验知识体系建立、wiki 内容经过若干轮运营积累后，方案生产的 wiki 素材质量才足以支撑高质量输出。届时评估 v4.0 启动。

**主要工作预览**（不做详细规划，待启动时完善）：
- 结构化方案草稿输出（query.md 新增草稿生成模式）
- md → 带品牌样式的 HTML
- HTML → PPTX（工具链待定）
- `outputs/` 目录（不进 git）

---

## 跨版本通用规范

### log.md 操作类型枚举（持续扩展）

| 操作类型 | 含义 | 引入版本 |
|---------|------|---------|
| INIT | 系统初始化 | v0.1 |
| INGEST | 摄入新材料（方案/文档类） | v0.1 |
| QUERY | 执行查询 | v0.1 |
| LINT | 健康检查 | v0.1 |
| VERSION-UPDATE | 版本覆盖更新 | v1.0 |
| ARCHIVE | 知识归档 | v1.0 |
| SCHEMA-UPDATE | Schema 或规则变更通知 | v1.1 |
| EXPERIENCE-INGEST | 摄入经验事件报告 | v2.1 |
| EXPERIENCE-ENRICH | 跨实体增益执行记录 | v2.1 |
| FEEDBACK | 对话式反馈反哺 | v2.1 |
| GRAPH-UPDATE | 图谱增量刷新 | v2.5 |
| EXTERNAL-INGEST | 外部知识摄入 | v3.0 |
| DRAFT-GENERATED | 方案草稿生成 | v4.0 |

---

### 目录结构全景（v3.0 完成后）

```
llm-wiki-kit/                   # 项目根目录
├── SCHEMA-CORE.md
├── CLAUDE.md / AGENTS.md / .cursorrules
├── README.md
├── ROADMAP.md
│
├── schema/
│   └── domain-config.xlsx      # 领域配置（企业替换此文件适配行业）
│
├── prompts/
│   ├── ingest.md               # 方案/文档类摄入
│   ├── ingest-experience.md    # v2.1 新增：经验事件报告摄入
│   ├── ingest-external.md      # v3.0 新增：外部知识摄入
│   ├── query.md
│   └── lint.md
│
├── tools/
│   ├── migrate_v1_1.py         # entity_id 批量补填（已完成）
│   └── ingest_batch.py         # v3.0 新增：服务端批量 Ingest
│
├── sources/                    # 内部原始材料（不进 git）
│   ├── proposals/
│   ├── competitors/
│   ├── patents/
│   ├── certificates/
│   ├── policies/
│   ├── reports/                # v2.1 新增：事件报告（机器生成）
│   ├── media/                  # v1.1 新增：多媒体资产原件
│   └── annotations/            # v1.1 新增：人工补充材料（可选）
│
├── world-sources/              # 外部原始材料（不进 git，v3.0 新增）
│
├── wiki-app/                   # 内部 Web 查询应用（JWT 认证，面向内部用户）
│
├── api-gateway/                # 对外 API Gateway（API Key 认证，面向外部系统）
│   ├── main.py                 # FastAPI 网关入口（限流 + 请求日志中间件）
│   ├── auth.py                 # API Key 认证 + 滑动窗口限流
│   ├── wiki_reader.py          # 知识库读取（共享 wiki/ 目录，零数据冗余）
│   ├── llm_client.py           # LLM 提供商封装
│   ├── routers/                # query / wiki / gateway 管理路由
│   ├── models/                 # Pydantic 请求/响应模型
│   └── .env.example
│
└── wiki/                       # 知识库主体（进 git）
    ├── index.md
    ├── log.md
    ├── config.yml              # v3.0 新增：触发配置
    ├── schema-suggestions.md   # v2.0 新增：自发现字段建议池
    ├── pending-clarifications.md  # v2.0 新增：冲突待裁决池
    ├── graph/                  # v2.5 新增：Graphify 知识图谱
    │   ├── graph.json
    │   ├── graph.html
    │   └── GRAPH_REPORT.md
    ├── assets/                 # v2.5 新增：媒体资产聚合索引
    │   └── index.md
    ├── experiences/            # v2.1 新增：经验知识
    │   ├── sessions/           # 事件型（接待/活动/案例）
    │   ├── monthly/            # 周期型（月报/季报）
    │   ├── lessons/            # 沉淀型（经验总结）
    │   └── README.md
    ├── external/               # v3.0 新增：外部知识
    ├── archive/                # v1.0 新增：归档知识
    ├── industries/
    ├── hall-types/             # 展厅行业示例，其他行业替换
    ├── proposal-stages/
    ├── modules/
    ├── competitors/
    ├── clients/
    ├── policies/
    └── credentials/
```

---

## 下一步行动

**当前状态（2026-04-22）**：v0.1 ~ v2.0 均已完成。

- 知识核心层架构稳定，wiki-app 生产运行正常
- v2.0 完成：Ingest 两阶段自发现字段、冲突澄清机制、pending-clarifications.md / schema-suggestions.md 均已就绪
- **本周新增**：`api-gateway/` — 将知识库核心能力封装为对外 REST API（API Key 认证 + 限流 + 访问日志），外部系统可直接接入，详见 [`api-gateway/README.md`](api-gateway/README.md)

**当前版本遗留验收（v1.0 / v1.1 / v2.0）**：

```
1. 用非展厅行业的 domain-config.xlsx 完成一次 Ingest，验证通用化效果
2. 对同一项目执行两次 Ingest（不同版本），验证版本管控和 history 块
3. Ingest 一个带资产引用的实体，验证 assets 字段写入和 scenarios 标签
4. 执行 Lint 检测，验证生命周期检测和归档建议
5. 用 api-gateway 接入一个外部系统，验证 API Key 全流程
```

**下一版本启动条件**：

```
v2.1 启动：有第一批事件报告（接待报告/运营报告）待摄入
  - 可与 api-gateway 接入工作并行推进
  - domain-config.xlsx 需先扩展 Experience Types Sheet

v2.5 启动（提前触发，满足任一）：
  - wiki 实体总数超过 150 页
  - 单次 Query 频繁出现 [内容已截断]
  - wiki/experiences/ 积累超过 30 个 session 事件

v3.0 启动：有明确的外部知识接入需求，或服务端批处理需求上线

v4.0 启动：wiki 内容经若干轮运营积累，方案生产的知识基础成熟后评估
```
