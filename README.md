# LLM Wiki Kit

> 工具无关、领域可配置、应用解耦的企业级 LLM 知识基础设施

替换一份 Excel 配置文件，即可为任意行业领域搭建一套结构化 AI 知识库；同一套知识库可同时驱动多个不同的 AI 应用场景。

---

## 核心理念

```
企业提供：原始材料（sources/）+ 领域配置（domain-config.xlsx）
系统输出：结构化知识库（wiki/）
```

**wiki 是纯粹的知识输出层，不绑定任何下游应用。** 各下游 AI 应用按需消费 wiki，互不干扰：

```
wiki/（知识层）
    ├─ 方案生产应用（wiki-app）
    ├─ AI 策展 / 数字人问答
    ├─ AI 陪练 / 智能推荐
    └─ 任意其他 AI 应用…
```

新增一个下游应用，无需修改 wiki 任何文件；更换行业只需替换 `domain-config.xlsx`，无需改代码。

---

## 架构

```
┌──────────────────────────────────────────────────────────┐
│  知识层（AI 驱动，本地操作）                                │
│                                                           │
│  schema/domain-config.xlsx  定义行业字段与分类枚举          │
│           ↓                                               │
│  sources/  →  prompts/ingest.md  →  wiki/                │
│  原始材料      LLM 摄入提示词         结构化知识库           │
│  （文档/多媒体）                   （Frontmatter + Markdown）│
└──────────────────────┬───────────────────────────────────┘
                       │  wiki/ 目录（标准输出，不感知下游）
          ┌────────────┼────────────┬─────────────┐
          ▼            ▼            ▼             ▼
     方案生产应用    AI 策展      智能问答      AI 陪练…
     （wiki-app）  （策展配屏）  （数字人）   （话术训练）
   各应用自定义过滤逻辑，按需消费 wiki 字段和资产引用
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

将原始材料放入 `sources/` 对应子目录（PDF / PPT / Word 放 `proposals/`，视频 / 图片 / HTML 放 `media/`，人工补充的讲解词等放 `annotations/`），在 Claude Code 或 Cursor 中执行：

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
│   ├── proposals/            # 文档类（PDF / PPT / Word）
│   ├── media/                # 多媒体资产（视频 / 图片 / HTML）
│   └── annotations/          # 人工补充材料（讲解词 / 问答对，可选）
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

## 核心特性

- **领域可配置**：替换 `domain-config.xlsx` 即可切换行业，无需改代码
- **应用解耦**：wiki 不感知任何下游应用，新增应用场景无需修改知识层；各应用自定义消费逻辑
- **资产引用**：Frontmatter `assets[]` 字段携带文件路径或在线 URL，策展 / 问答等应用可直接提取
- **场景标签**：`scenarios[]` 字段标注实体适用场景，下游应用快速精准过滤
- **正文分区**：`[narration]` / `[qa]` / `[training]` 等可选分区，不同应用按需提取对应内容
- **版本管控**：同一项目多次 Ingest 自动执行版本比对，旧值保存至 `history:` 块
- **知识生命周期**：三态模型（active / outdated / archived），Lint 自动检测过期政策和证书

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
| v1.1 | Decouple | 应用解耦 + 资产引用 + 场景标签 + 正文分区 | ✅ |
| v2.0 | Intelligence | 自发现字段 + 冲突澄清 + 反馈反哺 | 🔲 |
| v2.5 | Graph Layer | 知识图谱（Graphify 集成） | 🔲 |
| v3.0 | Expansion | 多媒体资产深化 + 外脑机制 + 自动触发 | 🔲 |
| v4.0 | Production | 方案生产闭环（md → HTML → PPT） | 🔲 |

详见 [ROADMAP.md](ROADMAP.md)

---

## License

MIT
