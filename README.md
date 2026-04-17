# LLM Wiki Kit

**工具无关、领域可配置的企业知识库框架**

通过替换 `schema/domain-config.xlsx`，即可为任意行业领域快速搭建一套完整的 LLM 知识管理系统。

---

## 架构概览

```
┌─────────────────────────────────────────────────────┐
│  知识层（company-wiki 模式）                          │
│  schema/domain-config.xlsx  →  定义领域字段与枚举     │
│  prompts/ingest.md          →  AI 驱动的知识摄入      │
│  wiki/                      →  LLM 生成的结构化知识库  │
└───────────────────┬─────────────────────────────────┘
                    │ wiki/ 目录（Markdown 文件）
┌───────────────────▼─────────────────────────────────┐
│  应用层（wiki-app）                                   │
│  FastAPI 后端 + 单页前端                              │
│  用户查询、方案生产、知识检索                           │
└─────────────────────────────────────────────────────┘
```

---

## 快速开始

### 1. 配置领域

编辑 `schema/domain-config.xlsx`，填写你的行业字段：

| Sheet | 内容 |
|-------|------|
| Sheet1 | 实体类型（对应 wiki/ 子目录） |
| Sheet2 | 字段清单（名称/类型/枚举值） |
| Sheet3 | 实体关联关系 |
| Sheet4 | 方案章节结构（v4.0 预留） |

> 文件内已附展厅行业的填写示例，参照修改即可。

### 2. 知识入库（Ingest）

将原始材料放入 `sources/proposals/`，然后在 Claude Code / Cursor 中执行：

```
# 粘贴 prompts/ingest.md 中的提示词，替换文件路径后运行
```

### 3. 部署 Web 应用

```bash
cd wiki-app
cp .env.example .env          # 填写 LLM API Key 和路径配置
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

配置说明见 `wiki-app/.env.example`。

### 4. 同步 wiki 内容到服务器

每次本地 Ingest 更新 wiki/ 后，将 wiki/ 目录上传至服务器对应路径：

```bash
rsync -avz wiki/ user@server:/path/to/wiki-app/wiki/
```

---

## 目录结构

```
llm-wiki-kit/
├── schema/
│   ├── SCHEMA-CORE.md        # 通用规则（无行业枚举）
│   └── domain-config.xlsx    # 领域配置（企业自定义）
│
├── prompts/
│   ├── ingest.md             # 知识摄入提示词
│   ├── query.md              # 知识查询提示词（AI 路径）
│   ├── lint.md               # 健康检查提示词
│   └── validate.md           # 可视化验证提示词
│
├── wiki/                     # 知识库（Ingest 后自动生成）
│   ├── archive/              # 已归档知识
│   └── ...                   # 由 domain-config 定义的子目录
│
├── sources/                  # 原始材料（不进 git）
│
├── wiki-app/                 # Web 应用
│   ├── app.py                # FastAPI 后端
│   ├── db.py                 # SQLite 数据库
│   ├── static/index.html     # 单页前端
│   ├── prompts/              # LLM 查询提示词模板（可后台修改）
│   └── .env.example          # 环境变量说明
│
├── SCHEMA.md                 # 向后兼容入口（指向 schema/）
├── CLAUDE.md                 # Claude Code 配置
├── AGENTS.md                 # 其他 AI 工具配置
├── .cursorrules              # Cursor 配置
└── ROADMAP.md                # 演进路线图
```

---

## 使用场景

| 领域 | 操作 |
|------|------|
| 展厅方案知识库（内置示例） | 直接使用，domain-config.xlsx 已填写 |
| 其他行业知识库 | 修改 domain-config.xlsx，重新 Ingest |
| 多套并行知识库 | clone 多份，各自配置独立 domain-config |

---

## 技术栈

- **知识层**：Markdown + YAML Frontmatter + LLM（Claude / Cursor）
- **应用层**：FastAPI · SQLite · Moonshot / Qwen API · Tailwind CSS
- **版本管控**：Git（知识框架） + 手动同步（wiki 内容）

---

## 版本

当前版本：**v1.0 Foundation**  
详见 [ROADMAP.md](ROADMAP.md)
