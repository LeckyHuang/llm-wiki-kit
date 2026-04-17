# company-wiki 演进路线图

> 本文档记录 company-wiki 知识库系统从初始框架到完整知识中台的分阶段演进计划。  
> 每个版本独立可交付，上一版本是下一版本的前提。  
> 最后更新：2026-04-17

---

## 愿景

构建一套**工具无关、领域可配置、自我进化**的企业级 LLM Wiki 知识管理系统：

- 企业提供原始材料（sources/）和领域配置（Schema），系统生长出对应的知识库
- 知识库不只存储结构化事实，还索引多媒体资产、追踪知识时效、区分内外部来源
- 最终支撑从"知识沉淀"到"生产级方案输出"的完整闭环

---

## 版本全景

| 版本 | 代号 | 核心主题 | 状态 |
|------|------|----------|------|
| v0.1 | Bootstrap | 框架初始化（已完成） + 首批 47 份方案入库 + wiki-app 生产部署 | ✅ 已完成 |
| v1.0 | Foundation | 通用化 + 版本管控 + 知识生命周期 | ✅ 已完成 |
| v2.0 | Intelligence | 自发现字段 + 冲突澄清 + 反馈反哺 | 🔲 待启动 |
| v2.5 | Graph Layer | 知识图谱关系层（Graphify 集成） | 🔲 待启动 |
| v3.0 | Expansion | 多媒体资产 + 外脑机制 + 自动触发 | 🔲 待启动 |
| v4.0 | Production | 方案生产闭环（md→html→PPT） | 🔲 待启动 |

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

- **Schema 通用性边界**：AI 直接操作路径（prompts/）已完全通用；wiki-app 的目录名（`industries/`、`hall-types/`）为硬编码，对同类 B2B 知识库可直接复用，跨度过大的领域需改 app.py 和前端
- **服务端 Ingest**：当前仍为本地操作，server-side Ingest pipeline 规划入 v3.0；阶段性方案见 ROADMAP v3.0 §3.3（可按"文件上传→触发 Ingest→自动写 wiki/"路径分3步落地）
- **旧页面 entity_id 补全**：现有客户案例页缺少 entity_id / version 字段，下次对该文件重新 Ingest 时顺手补充即可

---

## v2.0 Intelligence — 自发现字段 + 冲突澄清 + 反馈反哺

### 目标

让系统从"被动执行指令"升级为"主动学习和自我修正"：Ingest 能发现 Schema 未覆盖的知识维度，冲突知识能触发人工裁决，Query 中的用户修正能反向更新 wiki。

### 2.1 Ingest 自发现字段

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
- [ ] 更新 ingest.md，加入两阶段 Ingest 逻辑
- [ ] 定义 auto_discovered: 块的标准格式
- [ ] 创建 wiki/schema-suggestions.md 模板和填写规范

---

### 2.2 冲突检测与澄清机制

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
- [ ] 更新 ingest.md，加入冲突检测逻辑和三类冲突处理方式
- [ ] 创建 wiki/pending-clarifications.md 模板
- [ ] 更新 lint.md，将 pending-clarifications.md 纳入健康检查

---

### 2.3 交互反馈反哺 Wiki

**问题**：Query 生产方案的过程中，用户的每一次修改（"这个说法不对"、"实际上我们在这个行业的强项是X"）都是高价值知识，但目前全部流失。

**方案**：在 query.md 末尾增加"反馈捕获"环节：

Query 会话结束时，LLM 自动总结本次交互中发生的修正，提示用户确认：

```markdown
## 本次查询反馈捕获

以下修正被记录，请确认是否回写至 wiki：

1. [知识修正] 运营商行业-系统方案-核心卖点
   原值："统一管理平台"
   修正为："端到端自主可控"
   → [ ] 确认更新  [ ] 仅本次有效，不更新

2. [缺失知识] 发现 wiki 中缺少"项目交付周期"字段
   示例值：标准项目 4-6 个月
   → [ ] 新增至 wiki  [ ] 加入 schema-suggestions  [ ] 忽略

3. [表达偏好] 对政府客户使用"数字政务"优于"智慧城市"
   → [ ] 写入对应实体的 best-expression 字段  [ ] 忽略
```

用户确认后，LLM 执行对应的 wiki 更新，并在 log.md 中记录（来源标注为 `FEEDBACK`）。

**交付物**
- [ ] 更新 query.md，加入反馈捕获模块
- [ ] 在 SCHEMA-CORE.md 中定义 best-expression 字段规范
- [ ] 更新 log.md 格式，新增 `FEEDBACK` 操作类型

---

### v2.0 里程碑验收标准

- [ ] Ingest 一份新方案后，能在 schema-suggestions.md 中看到至少 3 条有价值的自发现字段建议
- [ ] 对同一实体的矛盾描述，pending-clarifications.md 能正确捕获并呈现
- [ ] 完成一次完整 Query 并通过反馈捕获成功更新 wiki 中至少 1 个字段

---

## v2.5 Graph Layer — 知识图谱关系层（Graphify 集成）

### 目标

在 v2.0 建立的知识实体基础上，引入 [Graphify](https://github.com/safishamsi/graphify) 作为 wiki 的**关系层**，解决三个核心问题：
- wiki 实体之间的语义关联关系目前依赖人工或隐式理解，缺乏结构化表达
- Query 随着 wiki 规模增长，token 消耗线性膨胀，需要图谱路由做前置过滤
- AMBIGUOUS 关系的自动发现，与 v2.0 的冲突澄清机制打通

> **Graphify 简介**：将代码、PDF、Markdown、图片等多模态文件转化为知识图谱（NetworkX），采用 Leiden 社区发现算法聚类（无需向量数据库），查询时 token 消耗最高可降低 71.5 倍。每条关系标注置信度：`EXTRACTED`（直接发现）/ `INFERRED`（推断）/ `AMBIGUOUS`（需人工复核）。

---

### 2.5.1 在 wiki/ 上建立知识图谱

**操作**：将 Graphify 作为 skill 安装后，在 wiki/ 目录执行：

```bash
/graphify ./wiki --mode deep
```

Graphify 将扫描所有 wiki Markdown 页面，提取知识实体节点和它们之间的语义关系，生成：

```
wiki/graph/
├── graph.json       # 持久化图谱数据（进 git，团队共享）
├── graph.html       # 可交互可视化（进 git）
└── GRAPH_REPORT.md  # 一页式关系摘要（进 git）
```

生成的关系示例：
```
[运营商行业] --常用方案类型--> [5G智慧展厅系统方案]   EXTRACTED 1.0
[5G智慧展厅] --竞品对标-->     [华为智能展厅]          INFERRED  0.82
[华为智能展厅] --信息来源-->   [competitors/huawei]    EXTRACTED 1.0
[投标方案模板] --适用行业-->   [运营商行业]            INFERRED  0.75
```

**与 Obsidian 的协作关系**：

| | Obsidian 图谱 | Graphify 图谱 |
|---|---|---|
| 关系来源 | 显式 `[[链接]]` | 语义提取 + 推断 |
| 置信度标注 | 无 | EXTRACTED / INFERRED / AMBIGUOUS |
| 社区聚类 | 无 | Leiden 算法自动分组 |
| 交互查询 | 基础浏览 | `/graphify query "问题"` |
| 路径追踪 | 无 | `/graphify path "实体A" "实体B"` |

Obsidian 负责日常内容浏览和编辑，Graphify 负责关系发现、聚类分析和查询优化，两者互补不冲突。

**交付物**
- [ ] 安装 Graphify skill（`graphify claude install`）
- [ ] 首次在 wiki/ 上运行 `/graphify . --mode deep`，生成初始图谱
- [ ] 创建 wiki/graph/ 目录，确认三个输出文件正常生成
- [ ] 将 wiki/graph/ 加入 git 跟踪（graph.json 和 graph.html 进 git）

---

### 2.5.2 AMBIGUOUS 关系 → 打通冲突澄清机制

**方案**：Graphify 标记为 `AMBIGUOUS` 的关系，自动追加写入 `wiki/pending-clarifications.md`（v2.0 已建立），格式统一：

```markdown
### [CONFLICT-G001] 关系待澄清（来自 Graphify）
- 实体A：modules/content-system.md
- 实体B：modules/operation-system.md
- 疑似关系："内容系统包含运营系统" vs "两者并列"
- 置信度：0.41（AMBIGUOUS）
- 建议裁决：[ ] A包含B  [ ] 并列关系  [ ] 无直接关系
```

用户在 Lint 周期中统一处理，裁决结果写回 wiki 并触发 `/graphify --update` 刷新图谱中该关系的置信度。

**交付物**
- [ ] 更新 lint.md prompt，加入读取 graph.json 中 AMBIGUOUS 关系并写入 pending-clarifications.md 的步骤
- [ ] 在 SCHEMA-CORE.md 中定义 Graphify 关系标注与 wiki 冲突机制的对应规则

---

### 2.5.3 Query 改为图谱路由模式

**问题**：随着 wiki 实体增长（预计 100+ 页），Query 时全量扫描 wiki 内容的 token 消耗会持续膨胀。

**方案**：Query 新增图谱路由前置步骤：

```
原 Query 流程：
  接收查询参数 → 扫描全部 wiki 页面 → LLM 合成输出

新 Query 流程（图谱路由）：
  接收查询参数
    → /graphify query "参数关键词"   ← 图谱层快速定位相关节点
    → 取出相关节点对应的 wiki 页面列表（精准子集）
    → 仅将该子集内容喂给 LLM 合成输出
```

实测 token 消耗可降低数十倍（Graphify 官方数据：混合语料场景降低 71.5 倍）。

**交付物**
- [ ] 更新 query.md prompt，加入图谱路由前置步骤
- [ ] 在 SCHEMA-CORE.md 中记录 Query 两阶段流程规范

---

### 2.5.4 Ingest 后自动刷新图谱

**方案**：每次 Ingest 完成、wiki 页面有更新后，追加执行图谱增量更新：

```bash
/graphify ./wiki --update    # 仅处理变更文件（SHA256 缓存机制）
```

此操作成本极低，不影响 Ingest 整体速度。后续接入 v3.0 自动触发机制后，可与 Ingest 形成联动。

**交付物**
- [ ] 更新 ingest.md prompt，末尾加入"执行 `/graphify ./wiki --update` 刷新图谱"步骤
- [ ] 在 wiki/config.yml（v3.0 引入）中预留 `graph.auto_update` 配置项

---

### 2.5.5 外脑图谱（为 v3.0 预埋）

v3.0 引入 world-sources/ 外部知识后，可对 `wiki/external/` 单独运行 Graphify，生成外部知识图谱，并与内部图谱建立跨域连接边（权重低于内部关系，反映来源可信度差异）。

此部分在 v2.5 仅做**接口预留**，不实现：在 graph.json 的 schema 中预留 `source_type: internal/external` 字段，便于 v3.0 合并双图谱时直接使用。

**交付物**
- [ ] 在 SCHEMA-CORE.md 中注明 graph.json 的 `source_type` 字段预留说明

---

### v2.5 里程碑验收标准

- [ ] `/graphify . --mode deep` 在 wiki/ 上成功运行，生成 graph.json / graph.html / GRAPH_REPORT.md
- [ ] graph.html 可在浏览器中交互浏览，节点点击能看到对应 wiki 实体内容
- [ ] AMBIGUOUS 关系自动出现在 pending-clarifications.md 中
- [ ] Query 通过图谱路由，相比全量扫描 token 消耗明显下降
- [ ] Ingest 新文件后执行 `--update`，图谱中出现新节点和关系

### v2.5 提前触发条件

v2.5 无需等待 v2.0 全部完成，当以下任一条件满足时应优先启动：

- `wiki/clients/` 目录体积超过 **400K**（当前 212K，约 100 份方案时触发）
- 单次 `/api/query` 响应中频繁出现 `[内容已截断]` 提示
- `MAX_WIKI_CHARS` 被迫调高至 120K 以上仍不够用

> **背景**：`clients/` 是增长最快的目录，随方案持续入库将线性膨胀。图谱路由是解决上下文膨胀的根本方案，不应因等待其他版本而延误。

---

## v3.0 Expansion — 多媒体资产 + 外脑机制 + 自动触发

### 目标

大幅扩展知识库的"感知范围"：向内打通多媒体资产索引，向外接入互联网知识补充，向下实现变更自动触发。

### 3.1 多媒体资产索引

**问题**：方案文件中的图表、效果图、架构图、案例视频等是极高价值的素材，但当前系统完全无法索引和检索。

**方案**：Ingest 时增加资产登记步骤：

每份 source 文件 Ingest 时，同步生成一个资产清单文件：

```
sources/proposals/2024-广州移动展厅-最终方案.pdf
→ wiki/assets/2024-guangzhou-mobile-assets.md
```

资产清单格式：
```markdown
---
source: proposals/2024-广州移动展厅-最终方案.pdf
entity_id: proj-2024-telecom-guangzhou-01
---

## 图表资产

| 资产ID | 类型 | 描述 | 页码/时间码 | 适用场景 |
|--------|------|------|-----------|---------|
| asset-001 | architecture-diagram | 系统整体架构图 | P12 | 系统方案章节 |
| asset-002 | floor-plan | 展厅平面布局图 | P18 | 空间设计章节 |
| asset-003 | photo | 竣工实景照片×6 | P35-40 | 案例展示 |
| asset-004 | flow-diagram | 内容运营流程图 | P22 | 运营方案章节 |
```

Query 时可按资产类型筛选：`资产类型:architecture-diagram 行业:运营商`，返回匹配的资产列表及其所在原始文件位置。

**交付物**
- [ ] 定义资产类型枚举（architecture-diagram / floor-plan / photo / flow-diagram / scan / video / other）
- [ ] 更新 ingest.md，加入资产登记步骤
- [ ] 创建 wiki/assets/ 目录
- [ ] 更新 query.md，支持按资产类型检索

---

### 3.2 外脑机制（World Sources）

**问题**：企业内部方案只反映自身经验，缺乏行业趋势、竞品动态、政策解读等外部视角，限制了知识库对商业策略和解决方案生产的支撑能力。

**方案**：构建与内部 wiki 并行的外部知识空间：

**目录结构**：
```
world-sources/           # 原始外部材料（不进 git，同 sources/）
  ├── industry-reports/  # 行业研究报告
  ├── competitor-web/    # 竞品官网/公开材料
  ├── policy-official/   # 政府政策原文
  └── news-articles/     # 行业新闻

wiki/external/           # 外部知识提炼（进 git，有明确标注）
  ├── index.md
  ├── industry-trends/
  ├── competitors/       # 与 wiki/competitors/ 互补
  └── policies/          # 与 wiki/policies/ 互补
```

**核心设计原则**：
- 每个外部 wiki 页面顶部必须有 `[EXTERNAL]` 醒目标注
- 每条知识点必须标注 `source_url` + `crawled_at` 时间戳
- 外部知识**按实体绑定生长**：Ingest 内部方案提取出"华为展厅"实体时，触发外部搜索补充华为展厅的公开信息，挂在同一实体下的 `external:` 分区块

**外部知识的 Ingest 触发逻辑**：
```
1. 完成内部 Ingest，提取出新实体列表
2. 对每个新实体，执行外部搜索（通过 web-search 工具或 agent-reach skill）
3. 提炼外部搜索结果 → 写入 wiki/external/
4. 在对应内部 wiki 页面增加 external_refs: 指针
```

**Query 时的筛选控制**：
```
默认：仅内部 wiki 参与检索
--include-external：内部 + 外部 wiki 均参与，外部结果标注来源
--external-only：仅用于了解外部视角（竞品研究、行业对标等）
```

**外部知识的维护**：
- Lint 检查时，对 `crawled_at` 超过 180 天的外部条目标记为"建议刷新"
- 政策类外部知识比照内部政策的生命周期管理

**交付物**
- [ ] 在 SCHEMA-CORE.md 中写入外部知识规范（标注要求、溯源规则）
- [ ] 创建 world-sources/ 和 wiki/external/ 目录结构
- [ ] 新增 prompts/ingest-external.md（外部知识专用 Ingest prompt）
- [ ] 更新 query.md，加入 internal/external 筛选控制
- [ ] 更新 lint.md，加入外部知识时效检测

---

### 3.3 自动触发机制

**问题**：当 sources/ 更新频繁时，手动触发 Ingest 效率低，容易遗漏。

**方案**：两种触发模式，通过配置文件切换：

```yaml
# wiki/config.yml（新增配置文件）

ingest:
  trigger_mode: manual          # manual / auto-confirm / auto-silent
  watch_paths:
    - sources/proposals/
    - sources/competitors/
  exclude_patterns:
    - "*.tmp"
    - "~$*"                     # Office 临时文件

lint:
  schedule: monthly             # monthly / weekly / manual
  auto_archive: false           # 是否自动执行归档（false=仅建议，需用户确认）
```

触发模式说明：
- `manual`：完全手动（默认，适合初期）
- `auto-confirm`：检测到新文件时提示用户确认再执行（推荐日常使用）
- `auto-silent`：静默自动 Ingest，完成后通知（适合批量场景，需谨慎）

**交付物**
- [ ] 创建 wiki/config.yml 及其说明文档
- [ ] 更新 SCHEMA-CORE.md，说明 config.yml 的作用和触发逻辑
- [ ] 更新 README.md，加入触发模式配置说明

---

### v3.0 里程碑验收标准

- [ ] Ingest 一份含图表的方案，wiki/assets/ 中出现对应资产清单
- [ ] 手动触发一次外部补充，wiki/external/ 中出现有溯源标注的外部知识页面
- [ ] Query 时通过 `--include-external` 能同时召回内外部知识且来源标注清晰

---

## v4.0 Production — 方案生产闭环

### 目标

将 wiki 知识库从"信息检索工具"升级为"方案生产基础设施"，实现从知识查询到生产级输出物的完整链路。

### 4.1 结构化方案草稿输出

**方案**：在 query.md 中新增"方案草稿生成"模式，Query 的输出不只是素材包，而是一份结构完整的方案草稿：

```markdown
## 方案草稿生成请求格式

行业: 运营商
客户层级: 省级
项目类型: 新建
方案阶段: 投标方案
输出格式: 草稿  ← 新增参数
```

输出的草稿遵循统一的章节结构（在 domain-config.xlsx 的 Sheet4 中定义），每个章节注明：
- 使用的 wiki 知识来源
- 建议引用的资产（图表/案例图）
- [需补充] 标注（wiki 中暂无对应知识的空位）

草稿以 Markdown 文件保存至 `outputs/drafts/` 目录（不进 git）。

**交付物**
- [ ] 在 domain-config.xlsx 增加 Sheet4：方案章节结构模板
- [ ] 更新 query.md，加入草稿生成模式
- [ ] 创建 outputs/drafts/ 目录（加入 .gitignore）

---

### 4.2 md → HTML 转换

**方案**：为草稿 Markdown 提供 HTML 转换支持，输出带企业品牌样式的 HTML 方案文档：

- 提供 CSS 模板（`assets/templates/proposal.css`），支持企业 Logo、色系配置
- 通过 Pandoc 执行转换（在 SCHEMA-CORE.md 中写入转换命令）
- HTML 输出至 `outputs/html/`

**交付物**
- [ ] 创建 assets/templates/ 目录，提供基础 proposal.css 模板
- [ ] 在 SCHEMA-CORE.md 中写入 md→HTML 转换命令和样式配置说明
- [ ] 创建 outputs/html/（加入 .gitignore）

---

### 4.3 HTML → PPT 转换

**方案**：这是链路中技术复杂度最高的一步，建议通过独立 agent/skill 实现，与 wiki 核心系统解耦：

- **方式A（推荐，低依赖）**：使用 Marp 将结构化 Markdown 直接转换为 PPT，在 domain-config.xlsx 中定义 Marp 主题配置
- **方式B（高质量，有依赖）**：通过 python-pptx 脚本，将 HTML 转换为格式精确的 PPTX 文件
- **方式C（工具集成）**：接入专门的 md→PPT skill（如 remotion-video 或类似工具）

最终选型在 v3.0 完成后根据工具链实际情况确定。

**交付物**
- [ ] 评估 Marp / python-pptx / 外部工具的适用性，确定选型
- [ ] 实现选定方案，输出至 `outputs/pptx/`
- [ ] 在 README.md 中记录完整的生产链路操作步骤

---

### v4.0 里程碑验收标准

- [ ] 输入行业+层级+阶段参数，能输出一份结构完整（含章节、来源标注、[需补充]标记）的 Markdown 草稿
- [ ] 草稿成功转换为带样式的 HTML 文件
- [ ] HTML 文件成功转换为可直接演示的 PPT 文件

---

## 跨版本通用规范

### log.md 操作类型枚举（持续扩展）

| 操作类型 | 含义 | 引入版本 |
|---------|------|---------|
| INIT | 系统初始化 | v0.1 |
| INGEST | 摄入新材料 | v0.1 |
| QUERY | 执行查询 | v0.1 |
| LINT | 健康检查 | v0.1 |
| VERSION-UPDATE | 版本覆盖更新 | v1.0 |
| ARCHIVE | 知识归档 | v1.0 |
| FEEDBACK | 交互反馈反哺 | v2.0 |
| GRAPH-UPDATE | 图谱增量刷新 | v2.5 |
| EXTERNAL-INGEST | 外部知识摄入 | v3.0 |
| DRAFT-GENERATED | 方案草稿生成 | v4.0 |

### 目录结构全景（v4.0 完成后）

```
company-wiki/
├── SCHEMA-CORE.md          # 通用核心规则
├── CLAUDE.md / AGENTS.md / .cursorrules
├── README.md
├── ROADMAP.md              # 本文件
│
├── schema/
│   └── domain-config.xlsx  # 领域配置（企业自定义）
│
├── prompts/
│   ├── ingest.md
│   ├── ingest-external.md  # v3.0 新增
│   ├── query.md
│   └── lint.md
│
├── sources/                # 内部原始材料（不进 git）
├── world-sources/          # 外部原始材料（不进 git）
├── outputs/                # 生成物（不进 git）
│   ├── drafts/
│   ├── html/
│   └── pptx/
│
├── assets/
│   └── templates/          # HTML/PPT 样式模板
│
└── wiki/                   # 知识库主体（进 git）
    ├── index.md
    ├── log.md
    ├── config.yml          # v3.0 新增
    ├── schema-suggestions.md   # v2.0 新增
    ├── pending-clarifications.md  # v2.0 新增
    ├── graph/              # Graphify 知识图谱  v2.5 新增
    │   ├── graph.json
    │   ├── graph.html
    │   └── GRAPH_REPORT.md
    ├── assets/             # 多媒体资产清单  v3.0 新增
    ├── external/           # 外部知识  v3.0 新增
    ├── archive/            # 归档知识  v1.0 新增
    ├── industries/
    ├── solution-types/
    ├── hall-types/
    ├── proposal-stages/
    ├── modules/
    ├── competitors/
    ├── clients/
    ├── policies/
    └── credentials/
```

---

## 下一步行动

**当前最优先**：在公司电脑上完成第一批 Ingest（激活 wiki 内容），同时启动 v1.0 的 Schema 通用化改造。只有 wiki 中有真实内容，后续版本的机制才有验证土壤。

```
立即可做：
1. git clone 至公司电脑
2. 将 50+ 份历史方案放入 sources/proposals/
3. 执行第一批 Ingest（优先运营商行业 3-4 份）
4. 观察 wiki/ 生成的内容，评估 Schema 的提取质量

并行启动 v1.0：
5. 重构 SCHEMA.md → SCHEMA-CORE.md
6. 制作 domain-config.xlsx 模板并填写展厅行业配置
```
