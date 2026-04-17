# Wiki Schema — 展厅方案知识库

> **v1.0 重构说明**：本文件已拆分为两层。
> - **通用规则**（目录结构、页面格式、操作规则、生命周期）→ `schema/SCHEMA-CORE.md`
> - **领域配置**（行业枚举、字段清单、关联关系）→ `schema/domain-config.xlsx`
>
> 本文件保留为**向后兼容入口**，所有新的 wiki 操作请以 `schema/SCHEMA-CORE.md` 为准。

---

## 快速导航

| 查询目的 | 阅读文件 |
|---------|---------|
| 页面格式规范 / 操作规则 / 版本管控 / 生命周期 | `schema/SCHEMA-CORE.md` |
| 行业类型 / 展厅类型 / 字段枚举值 | `schema/domain-config.xlsx` Sheet2 |
| 实体类型与目录映射 | `schema/domain-config.xlsx` Sheet1 |
| 实体间关联关系 | `schema/domain-config.xlsx` Sheet3 |

---

## 领域配置（展厅行业专用枚举值）

> 以下枚举值迁移自 v0.1 SCHEMA.md，已同步写入 `schema/domain-config.xlsx`。  
> 本节仅供快速人工查阅，**LLM 操作请读取 domain-config.xlsx**。

### 行业类型

参照 `schema/domain-config.xlsx` Sheet2，字段名 `industry`，枚举值：
- 通信/运营商（电信、移动、联通等）
- 工业/制造
- 金融
- 政府/政务
- 能源
- 其他

### 项目类型

参照 `schema/domain-config.xlsx` Sheet2，字段名 `project_type`，枚举值：
- 新建
- 升级
- 运营
- 复合型（升级+运营、新建+运营等）

### 展厅类型

参照 `schema/domain-config.xlsx` Sheet2，字段名 `hall_type`，枚举值：
- 品牌形象展厅
- 数智体验中心
- 党建教育展厅
- 企业文化展厅
- 企业形象展厅
- 企业营销展厅
- 商务交流中心

### 方案阶段

参照 `schema/domain-config.xlsx` Sheet2，字段名 `proposal_stage`，枚举值：
- 初步规划 — 论证期，偏"为什么做"
- 规划方案 — 方向性，偏宏观蓝图
- 汇报方案 — 向上级汇报确认
- 应标方案 — 针对客户 RFP 精准对标
- 设计方案 — 含技术实施细节
- 落地方案 — 执行向，含具体实施计划

### 客户层级

参照 `schema/domain-config.xlsx` Sheet2，字段名 `client_level`，枚举值：
- 集团级
- 省级
- 地市级
- 区域级

### 方案内容组合

参照 `schema/domain-config.xlsx` Sheet2，字段名 `content_types`，可多选：
- 内容、运营、系统

---

## 经验教训与统一规范（运营中积累，勿删）

以下来自多次 Ingest 实践总结的踩坑记录，后续操作必须遵守。

### 1. YAML 头部字段必须完整（v1.0 新增 entity_id / version / sources）

客户案例页必须包含（完整字段见 `schema/SCHEMA-CORE.md` §2.1）：

```yaml
---
title: 页面标题
type: client
tags: [标签1, 标签2]
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: active
entity_id: client-2024-telecom-guangzhou-01
version: v1
industry: 通信/运营商
hall_type: 品牌形象展厅
proposal_stage: 应标方案
client_level: 省级
result: 中标
sources:
  - proposals/2024-广州移动展厅-最终方案.pdf
---
```

即使某些字段无法直接提取，也要根据上下文推断填写，不能留空。

### 2. Index 索引必须叠加更新（禁止覆盖！）

- `wiki/index.md`：按行业/类型/阶段汇总，**每次追加新分类和统计**
- `wiki/clients/index.md`：客户案例汇总，**按行业分组追加**
- 更新原则：读取现有内容 → 在原有基础上增加新内容 → 更新统计数字

### 3. 文件归档路径统一

- PDF 源文件统一放入 `sources/proposals/`（支持子文件夹分类）
- `sources` frontmatter 字段需包含相对路径：`sources: [电网类/江门供电局xxx.pdf]`

### 4. 友商方案特殊处理

- 内容只写入 `wiki/competitors/`，不污染己方模板
- 重点提取：技术方案特点、价格信号、话术风格、薄弱点

### 5. 证书/专利必须记录有效期

- 证书：必须填写 `expiry_date`，Lint 检测临期（≤90天）和过期
- 专利：填写授权日期，`expiry_date` 可留空

---

*最后更新：2026-04-17 | v1.0 重构，领域枚举已迁移至 schema/domain-config.xlsx*
