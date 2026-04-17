# SCHEMA-CORE — 通用核心规则

本文件是 company-wiki 知识库系统的**通用规则层**，与任何行业领域无关。  
行业枚举、字段清单、关联关系等**领域配置**均存放在 `schema/domain-config.xlsx`。

> 上一版本：`SCHEMA.md`（v0.1，硬编码展厅行业）→ 已重构为本文件 + domain-config.xlsx（v1.0）

---

## 一、目录结构规范

```
sources/                    # 原始材料（只读，不修改，不进 git）
  proposals/                # 己方历史方案（支持子文件夹分类）
  competitors/              # 友商方案（竞品情报）
  patents/                  # 发明专利文件
  certificates/             # 资质证书文件
  policies/                 # 行业政策文件

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

# ── v1.0 新增字段 ──────────────────────────
entity_id: <类型前缀>-<年份>-<行业缩写>-<地点缩写>-<序号>
# 示例：client-2024-telecom-guangzhou-01
version: v1
sources:
  - proposals/文件名.pdf   # 按版本追加，不覆盖
---
```

- `status: outdated` — 内容可能过时，Query 时降权提示，不自动排除
- `status: archived` — 已确认过时，移入 `wiki/archive/`，**不参与任何 Query**
- 每次修改必须更新 `updated` 字段

### 2.2 Version History 块（可选）

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

### 2.3 entity_id 命名规则

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

## 三、双路径同步规则（Query 路径）

系统存在两条并行的 Query 路径，每次变更任一路径的查询逻辑时，必须同步评估另一路径：

| 路径 | 入口 | 适用场景 | 过滤逻辑所在层 |
|------|------|----------|--------------|
| AI 直接操作 | `prompts/query.md` | Claude/Cursor 直接读写 wiki | Prompt 文字规则 |
| Web 应用 | `wiki-app/app.py` `/api/query` | 生产环境前端用户 | 后端代码硬过滤 |

**同步清单**（每次变更时对照）：
1. 新增过滤维度 → 两侧都要加
2. 调整加载目录 → 两侧都要调
3. 修改输出格式 → 两侧都要改
4. 变更操作后在 `wiki/log.md` 记录变更类型（参见日志格式规范）

**已实现的 wiki-app 硬过滤**（截至 v1.0）：
- ✅ 行业维度：INDUSTRY_MAP 精准映射到子目录
- ✅ 展厅类型：HALL_MAP 精准映射
- ✅ 勾选控制：competitors / policies / credentials 按需加载
- ✅ clients 与 credentials 解耦，独立控制
- ✅ 随手问（/api/chat）不加载 clients，字符上限收紧
- ✅ `status: archived` 页面不进入 Query 上下文
- ✅ `status: outdated` 页面带 ⚠️ 提示后仍参与 Query

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
| Query | `prompts/query.md` | 为新方案生产提供素材 |
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
| FEEDBACK | 交互反馈反哺（v2.0 引入）|
| SYNC-CHECK | 双路径同步评估记录 |
