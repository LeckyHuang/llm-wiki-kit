# wiki/assets/ 目录说明

本目录存放全库媒体资产的聚合索引，由 `prompts/lint.md` 检查项 9 自动生成和维护。**无需手动编辑。**

## 文件说明

- `index.md`：全库资产聚合索引，按类型 / 按实体 / 跨事件使用记录三个维度组织

## 数据来源

- 各 wiki 实体 frontmatter 中的 `assets[]` 字段（v1.1 引入）
- 各 `experience` 实体 frontmatter 中的 `exhibited_assets[]` 字段（v2.1 引入）

## 维护方式

每次执行 Lint（`prompts/lint.md`）时，自动重新扫描全库并生成 `index.md`。

## 使用方式

- **查找指定类型资产**：在 `index.md` 的"按类型检索"区段查找
- **查找某实体引用的资产**：在"按实体检索"区段查找
- **评估资产价值**：在"跨事件使用记录"中，高频资产内容价值强，零引用资产评估下线
- **通过 Query 检索**：使用 `prompts/query.md` 中的"资产检索查询"模板
