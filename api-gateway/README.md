# Wiki API Gateway

将 [llm-wiki-kit](https://github.com/LeckyHuang/llm-wiki-kit) 的核心知识库能力封装为标准 REST API，供外部系统（CRM、移动 App、BI 工具、机器人等）接入。

## 架构关系

```
外部应用（CRM / App / 机器人 ...）
        │  X-API-Key: wk_live_xxx
        ▼
  api-gateway/  ← 本服务（对外）
        │  共享 wiki/ 目录
        ▼
    wiki/  知识层
        ▲
  wiki-app/  ← 内部 Web 应用（不变）
```

两个服务**共享同一个 `wiki/` 目录**，独立运行，互不干扰。

---

## 快速启动

```bash
cd api-gateway
cp .env.example .env        # 按需填写配置项
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001
```

- **Swagger 文档**：`http://localhost:8001/docs`
- **ReDoc 文档**：`http://localhost:8001/redoc`
- **健康检查**：`http://localhost:8001/health`

---

## 认证方式

### 业务接口：API Key

在请求头中携带：

```
X-API-Key: wk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 管理接口：Admin Key

在请求头中携带：

```
X-Admin-Key: <GATEWAY_ADMIN_KEY 配置的值>
```

---

## 开发调试：万能 Key

> 适合本地联调阶段，无需为每个调试应用单独注册 Key。

在 `.env` 中设置：

```env
DEV_API_KEY=my-local-dev-key
```

设置后，使用该 Key 可直接调用所有业务接口，**无需数据库注册、无限速**。  
**生产环境删除此行或留空，功能自动关闭。**

---

## 接入新应用（完整流程）

### 第一步：注册应用

```bash
curl -X POST http://localhost:8001/v1/apps \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: your_admin_key" \
  -d '{
    "name": "my-crm",
    "description": "CRM 系统集成",
    "scopes": "query,chat,wiki",
    "rate_limit": 60
  }'
```

### 第二步：创建 API Key

```bash
# 使用第一步返回的 app id
curl -X POST http://localhost:8001/v1/apps/1/keys \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: your_admin_key" \
  -d '{"label": "production"}'
```

> ⚠️ `api_key` 字段**仅在此响应中出现一次**，请立即保存。

### 第三步：调用业务接口

```bash
curl -X POST http://localhost:8001/v1/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: wk_live_xxxxxx" \
  -d '{
    "industry": "通信",
    "hall_type": "企业展厅",
    "project_type": "新建",
    "include_competitors": true
  }'
```

---

## API 接口参考

### 业务接口（需要 X-API-Key）

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| `POST` | `/v1/query` | `query` | 结构化知识查询，调用 LLM 生成方案素材摘要 |
| `POST` | `/v1/chat` | `chat` | 自由问答，针对知识库任意提问 |
| `GET` | `/v1/wiki/options` | `wiki` | 获取可用的行业、展厅类型等枚举值 |
| `GET` | `/v1/wiki/stats` | `wiki` | 知识库各目录词条数量统计 |
| `GET` | `/v1/wiki/entities` | `wiki` | 实体元数据列表（支持按子目录过滤） |

#### POST /v1/query

```json
// 请求体
{
  "industry": "通信",           // 目标行业，留空不限
  "hall_type": "企业展厅",      // 展厅类型，留空不限
  "project_type": "新建",       // 新建 / 改造升级 / 咨询规划 / 运营维护
  "include_competitors": false, // 是否加载竞品内容
  "include_policies": false,    // 是否加载政策依据
  "include_credentials": false, // 是否加载资质案例
  "question": "重点关注沉浸式体验模块",  // 补充说明（可选）
  "custom_prompt": null         // 自定义提示词，覆盖默认模板（可选）
}

// 响应体
{
  "result": "## 相关历史案例\n...",  // LLM 生成的知识摘要
  "wiki_chars_used": 12400,          // 本次加载的知识库字符数
  "provider": "moonshot"             // 使用的 LLM 提供商
}
```

#### POST /v1/chat

```json
// 请求体
{ "message": "我们在政务行业有哪些成功案例？" }

// 响应体
{ "result": "...", "wiki_chars_used": 8200, "provider": "moonshot" }
```

#### GET /v1/wiki/options

```json
// 响应体
{
  "industries": ["通信", "金融", "政务", "..."],
  "hall_types": ["企业展厅", "政务大厅", "..."],
  "project_types": ["新建", "改造升级", "咨询规划", "运营维护"]
}
```

#### GET /v1/wiki/entities?subdir=modules

```json
// 响应体（每个对象为一个词条的 frontmatter 元数据）
[
  { "_file": "多媒体互动", "_dir": "modules", "status": "active", ... },
  ...
]
```

---

### 管理接口（需要 X-Admin-Key）

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/v1/apps` | 列出所有注册应用 |
| `POST` | `/v1/apps` | 注册新应用 |
| `GET` | `/v1/apps/{app_id}` | 获取应用详情 |
| `PATCH` | `/v1/apps/{app_id}` | 更新应用信息（支持部分更新） |
| `DELETE` | `/v1/apps/{app_id}` | 停用应用（软删除） |
| `GET` | `/v1/apps/{app_id}/keys` | 列出应用的所有 API Key |
| `POST` | `/v1/apps/{app_id}/keys` | 为应用创建新 API Key |
| `DELETE` | `/v1/apps/{app_id}/keys/{key_id}` | 吊销 API Key |
| `GET` | `/v1/gateway/logs` | 查看访问日志（支持按 app_id、日期过滤） |

#### POST /v1/apps 请求体

```json
{
  "name": "my-app",           // 唯一名称
  "description": "描述",
  "contact": "dev@example.com",
  "scopes": "query,chat,wiki", // 可选值：query / chat / wiki
  "rate_limit": 60             // 次/分钟
}
```

#### PATCH /v1/apps/{id} 请求体（全部字段可选）

```json
{
  "description": "新描述",
  "scopes": "query",
  "rate_limit": 120,
  "is_active": true
}
```

---

### 系统接口（公开）

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 健康检查，返回 wiki 统计 + LLM 连通性 |
| `GET` | `/` | 服务基本信息 |
| `GET` | `/docs` | Swagger UI 交互文档 |
| `GET` | `/redoc` | ReDoc 文档 |

---

## 权限范围（Scopes）

| Scope | 覆盖接口 | 说明 |
|-------|---------|------|
| `query` | `POST /v1/query` | 结构化查询（调用 LLM） |
| `chat` | `POST /v1/chat` | 自由问答（调用 LLM） |
| `wiki` | `GET /v1/wiki/*` | 知识库元数据浏览（不调用 LLM） |

---

## 错误码说明

| HTTP 状态码 | 含义 |
|------------|------|
| `401` | 缺少或无效的认证信息 |
| `403` | 认证通过但无对应权限（scope 不足或应用已停用） |
| `404` | 资源不存在 |
| `409` | 冲突（如应用名已存在） |
| `429` | 请求频率超出限额，响应头含 `Retry-After: 60` |
| `502` | LLM 调用失败（上游问题） |
| `503` | LLM API Key 未配置 |

---

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WIKI_PATH` | `../wiki` | wiki 目录路径（与 wiki-app 共享） |
| `LLM_PROVIDER` | `moonshot` | LLM 提供商：`moonshot` / `qwen` |
| `MOONSHOT_API_KEY` | — | Moonshot API Key |
| `QWEN_API_KEY` | — | Qwen API Key |
| `MAX_WIKI_CHARS` | `80000` | query 接口最大加载字符数 |
| `MAX_CHAT_WIKI_CHARS` | `40000` | chat 接口最大加载字符数 |
| `GW_DB_PATH` | `./gateway.db` | Gateway 数据库路径 |
| `GATEWAY_ADMIN_KEY` | 自动生成 | 管理员主密钥（生产环境必须显式配置） |
| `DEFAULT_RATE_LIMIT` | `60` | 默认限流：次/分钟 |
| `DEV_API_KEY` | 空（关闭） | 开发调试万能密钥，生产环境留空 |
