# LLM Wiki Kit

> 工具无关、领域可配置的企业级 LLM 知识管理框架

替换一份 Excel 配置文件，即可为任意行业领域搭建一套完整的 AI 知识库系统。

---

## 核心理念

```
企业提供：原始材料（sources/）+ 领域配置（domain-config.xlsx）
系统输出：结构化知识库（wiki/）+ 可部署的 Web 查询应用（wiki-app/）
```

知识库由 LLM 自动生成和维护，Web 应用供团队成员日常查询使用。两者通过 `wiki/` 目录（Markdown 文件）解耦，独立演进。

---

## 架构

```
┌─────────────────────────────────────────────────────────┐
│  知识层（AI 驱动，本地操作）                               │
│                                                          │
│  schema/domain-config.xlsx  定义行业字段与分类枚举         │
│           ↓                                              │
│  sources/  →  prompts/ingest.md  →  wiki/               │
│  原始材料      LLM 摄入提示词         结构化知识库          │
└──────────────────────┬──────────────────────────────────┘
                       │  wiki/ 目录（Markdown 文件）
┌──────────────────────▼──────────────────────────────────┐
│  应用层（wiki-app，部署至服务器）                           │
│                                                          │
│  FastAPI 后端  +  单页前端  +  SQLite                     │
│  方案查询  /  方案概算  /  随手问  /  管理后台              │
└─────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 第一步：配置你的行业领域

编辑 `schema/domain-config.xlsx`，定义你的知识结构：

| Sheet | 内容 | 示例（内置展厅行业） |
|-------|------|------------------|
| Sheet1 | 实体类型与目录映射 | 客户案例、竞品画像、政策依据… |
| Sheet2 | 字段清单与枚举值 | 行业、展厅类型、方案阶段… |
| Sheet3 | 实体关联关系 | 客户案例 → 所属行业 |
| Sheet4 | 方案章节结构（v4.0 预留） | - |

> 文件内已内置**展厅行业**的完整配置示例，参照修改即可适配其他领域。

### 第二步：知识入库（Ingest）

将原始材料（PDF / PPT / Word）放入 `sources/proposals/`，在 Claude Code 或 Cursor 中执行：

```
# 复制 prompts/ingest.md 的内容给 LLM，替换文件路径后运行
```

LLM 将自动读取 `domain-config.xlsx`，提取关键信息并写入 `wiki/` 目录。

### 第三步：部署 Web 应用

```bash
cd wiki-app
cp .env.example .env      # 填写 LLM API Key（支持 Moonshot / Qwen）
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

### 第四步：同步知识库到服务器

本地 Ingest 更新 `wiki/` 后，推送到服务器：

```bash
rsync -avz wiki/ user@your-server:/path/to/wiki-app/wiki/
```

---

## 目录结构

```
llm-wiki-kit/
│
├── schema/
│   ├── SCHEMA-CORE.md        # 通用规则（与领域无关）
│   └── domain-config.xlsx    # 领域配置（企业自定义）
│
├── prompts/
│   ├── ingest.md             # 知识摄入（含版本管控）
│   ├── query.md              # 知识查询（AI 直接操作路径）
│   ├── lint.md               # 健康检查（生命周期检测）
│   └── validate.md           # Obsidian Canvas 可视化验证
│
├── wiki/                     # 知识库（Ingest 后自动生成，不进 git）
│   └── archive/              # 已归档知识
│
├── sources/                  # 原始材料（不进 git）
│
├── wiki-app/                 # Web 查询应用
│   ├── app.py                # FastAPI 后端（含生命周期过滤）
│   ├── db.py                 # SQLite 数据库
│   ├── static/index.html     # 单页前端
│   ├── prompts/              # LLM 提示词（可后台热更新）
│   └── .env.example          # 环境变量说明
│
├── SCHEMA.md                 # 向后兼容入口（v0.1 遗留）
├── CLAUDE.md                 # Claude Code 配置
├── AGENTS.md                 # 其他 AI 工具配置
├── .cursorrules              # Cursor 配置
└── ROADMAP.md                # 演进路线图
```

---

## 核心特性（v1.0）

- **领域可配置**：替换 `domain-config.xlsx` 即可切换行业，无需改代码
- **版本管控**：同一项目多次 Ingest 自动执行版本比对，旧值保存至 `history:` 块
- **知识生命周期**：三态模型（active / outdated / archived），Lint 自动检测过期政策和证书
- **双路径查询**：AI 直接操作路径（prompts/）+ Web 应用路径（wiki-app/）同步维护
- **status 过滤**：wiki-app 自动跳过 `archived` 页面，`outdated` 页面带 ⚠️ 提示

---

## 多知识库部署

同一套框架，不同行业只需 clone 后替换配置：

```bash
git clone https://github.com/LeckyHuang/llm-wiki-kit.git my-wiki
cd my-wiki
# 编辑 schema/domain-config.xlsx → 填写新行业配置
# 放入 sources/ 原始材料 → 执行 Ingest → 部署 wiki-app
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 知识摄入 | Claude Code / Cursor + LLM |
| 知识存储 | Markdown + YAML Frontmatter |
| Web 后端 | FastAPI · Python · SQLite |
| Web 前端 | 原生 HTML/CSS/JS · Tailwind CSS |
| LLM 接入 | Moonshot（moonshot-v1-128k）/ Qwen（qwen-long） |
| 可视化 | Obsidian + Dataview 插件 |

---

## 路线图

| 版本 | 代号 | 核心主题 | 状态 |
|------|------|----------|------|
| v0.1 | Bootstrap | 框架初始化 + 首批入库 + 生产部署 | ✅ |
| v1.0 | Foundation | 通用化 + 版本管控 + 生命周期 | ✅ |
| v2.0 | Intelligence | 自发现字段 + 冲突澄清 + 反馈反哺 | 🔲 |
| v2.5 | Graph Layer | 知识图谱（Graphify 集成） | 🔲 |
| v3.0 | Expansion | 多媒体资产 + 外脑机制 + 服务端 Ingest | 🔲 |
| v4.0 | Production | 方案生产闭环（md → HTML → PPT） | 🔲 |

详见 [ROADMAP.md](ROADMAP.md)

---

## License

MIT
