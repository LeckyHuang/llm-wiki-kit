# llm-wiki-kit 接入手册

## 一、系统信息

| 项目 | 说明 |
|------|------|
| 服务器地址 | `<服务器IP>`（替换为实际 IP） |
| 管理界面 | `http://<服务器IP>:8080` — wiki-app-hub 内部管理 |
| API 入口 | `http://<服务器IP>:8081` — api-gateway 对外接口 |
| API 文档 | `http://<服务器IP>:8081/docs` — Swagger UI |
| 健康检查 | `http://<服务器IP>:8081/health` |
| LLM 主力模型 | kimi-k2.6 (moonshot) |
| LLM 副模型 | qwen3.6-plus (qwen) |

---

## 二、认证机制

所有 `/v1/` 业务接口在请求头中携带 API Key：

```
X-API-Key: wk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

管理接口（注册应用、创建 Key）使用管理员密钥：

```
X-Admin-Key: <GATEWAY_ADMIN_KEY>
```

---

## 三、接入第一步：注册应用 & 获取 API Key

> 以下操作由管理员在服务器上执行。

### 3.1 注册应用

```powershell
$adminKey = "<GATEWAY_ADMIN_KEY>"

# 注册一个应用
$body = '{"name":"你的应用名称","scopes":["query","chat"],"rate_limit":60}'
Invoke-RestMethod -Uri "http://127.0.0.1:8081/v1/apps" `
  -Method Post `
  -Headers @{"X-Admin-Key"=$adminKey; "Content-Type"="application/json"} `
  -Body $body
```

返回示例：

```json
{
  "id": 1,
  "name": "你的应用名称",
  "scopes": "query,chat",
  "rate_limit": 60,
  "is_active": true,
  "created_at": "2026-04-28 13:00:00"
}
```

记下返回的 `id`。

### 3.2 获取 API Key

```powershell
$keyBody = '{"label":"生产环境Key"}'
Invoke-RestMethod -Uri "http://127.0.0.1:8081/v1/apps/1/keys" `
  -Method Post `
  -Headers @{"X-Admin-Key"=$adminKey; "Content-Type"="application/json"} `
  -Body $keyBody
```

返回示例：

```json
{
  "id": 1,
  "label": "生产环境Key",
  "key_prefix": "wk_live_abcd1234...",
  "api_key": "wk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "created_at": "2026-04-28 13:01:00"
}
```

> **`api_key` 仅显示一次！请立即妥善保存。**

### 3.3 权限范围 (Scopes)

| Scope | 允许访问的接口 |
|-------|---------------|
| `query` | `POST /v1/query`、`POST /v1/retrieve`、`POST /v1/ingest`、`GET /v1/ingest/*` |
| `chat` | `POST /v1/chat` |
| `wiki` | `GET /v1/wiki/*` |

> 注册应用时可按需组合，如 `"query,chat,wiki"`。

---

## 四、展项文件库系统对接

文件库系统通过 Ingest 接口将文件推送到知识库。

### 4.1 前置准备

1. 按第三章步骤注册应用，scopes 填 `["query"]`
2. 拿到 API Key

### 4.2 半自动模式（推荐）

文件上传后进入人工校对流程，管理员在 wiki-app-hub 界面确认后入库：

```python
import requests

API_BASE = "http://<服务器IP>:8081"
API_KEY = "wk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 上传文件（auto_commit=false）
with open("展厅方案.pdf", "rb") as f:
    resp = requests.post(
        f"{API_BASE}/v1/ingest",
        headers={"X-API-Key": API_KEY},
        data={"auto_commit": "false"},
        files={"file": f},
    )

data = resp.json()
print(f"任务ID: {data['task_id']}")
print(f"状态: {data['status']}")          # pending_review
print(f"预览: {data['preview']}")
```

管理员登录 `http://<服务器IP>:8080`，在「外部待入库」Tab 中校对后确认入库。

### 4.3 全自动模式

```python
import requests

API_BASE = "http://<服务器IP>:8081"
API_KEY = "wk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

with open("展厅方案.pdf", "rb") as f:
    resp = requests.post(
        f"{API_BASE}/v1/ingest",
        headers={"X-API-Key": API_KEY},
        data={"auto_commit": "true"},
        files={"file": f},
    )

data = resp.json()
print(data)
# {"task_id": "ing_abc123", "status": "committed", "entity_path": "cases/展厅方案", ...}
```

### 4.4 支持的文件格式

| 格式 | 说明 |
|------|------|
| `.pdf` | PDF 文档 |
| `.pptx` | PowerPoint 演示文稿 |
| `.docx` | Word 文档 |
| `.txt` | 纯文本 |
| `.md` | Markdown |

### 4.5 查询任务状态

```python
resp = requests.get(
    f"{API_BASE}/v1/ingest/ing_abc123",
    headers={"X-API-Key": API_KEY},
)
print(resp.json())
```

### 4.6 注意事项

- 文件大小限制：50MB（可调整 `MAX_INGEST_FILE_MB`）
- nginx 层限制：60MB（`client_max_body_size`）
- 请求超时：300 秒（SSE 流式输出模式）
- 建议对批量文件逐个提交，每个文件间隔 2~3 秒

---

## 五、AI 应用对接

AI 应用通过 Query/Chat 接口获取知识库上下文，用于增强 LLM 回答质量。

### 5.1 前置准备

1. 按第三章步骤注册应用，scopes 填 `["query","chat"]`
2. 拿到 API Key
3. 如需前端 JS 直调，在 `api-gateway/.env` 中配置 `CORS_ORIGINS`，重启服务

### 5.2 结构化查询（推荐）

适合需要特定领域知识的场景，返回结构化的知识摘要。

```python
import requests

API_BASE = "http://<服务器IP>:8081"
API_KEY = "wk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

resp = requests.post(
    f"{API_BASE}/v1/query",
    headers={
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
    },
    json={
        "industry": "文博",
        "hall_type": "历史文化展厅",
        "project_type": "新建",
        "include_competitors": True,
        "include_policies": True,
        "include_credentials": False,
        "question": "有哪些互动装置可以参考？",
    },
)

data = resp.json()
context = data["result"]           # 这就是给 AI 的知识库上下文
chars_used = data["wiki_chars_used"]  # 消耗的字符数
```

**请求参数说明：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `industry` | string | 否 | 行业/领域筛选，如"文博"、"金融"、"政务" |
| `hall_type` | string | 否 | 二级分类，如"历史文化展厅"、"品牌旗舰店" |
| `project_type` | string | 否 | 项目阶段，如"新建"、"改造升级" |
| `include_competitors` | bool | 否 | 是否加载竞品参考（默认 false） |
| `include_policies` | bool | 否 | 是否加载政策依据（默认 false） |
| `include_credentials` | bool | 否 | 是否加载资质案例（默认 false） |
| `question` | string | 否 | 补充问题，附加到查询末尾 |
| `custom_prompt` | string | 否 | 自定义查询指令，完全接管 prompt（高级用法） |

> `industry`、`hall_type`、`project_type` 的具体可用值可通过 `GET /v1/wiki/options` 动态获取。

### 5.3 自由问答

适合开放式问题，自动加载广泛的知识库内容。

```python
resp = requests.post(
    f"{API_BASE}/v1/chat",
    headers={
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
    },
    json={
        "message": "展厅声光电技术有哪些最新趋势？",
    },
)

answer = resp.json()["result"]
```

### 5.4 纯检索（不调用 LLM 总结）

返回原始知识片段，适合需要精确原文引用、或自行做 RAG 的场景。

```python
resp = requests.post(
    f"{API_BASE}/v1/retrieve",
    headers={
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
    },
    json={
        "query": "互动投影",
        "entity_type": "modules",
        "status": "active",
        "tags": ["互动装置"],
        "limit": 5,
        "max_chars_per_result": 2000,
        "rerank": False,
    },
)

for r in resp.json()["results"]:
    print(f"标题: {r['title']}")
    print(f"来源: {r['source']}")
    print(f"相关性: {r['relevance_score']}")
    print(f"内容: {r['content'][:200]}...")
    print("---")
```

### 5.5 获取知识库选项（前端下拉菜单）

```python
resp = requests.get(
    f"{API_BASE}/v1/wiki/options",
    headers={"X-API-Key": API_KEY},
)
options = resp.json()
# {"industries": ["文博", "金融", "政务"], "hall-types": [...], ...}
```

### 5.6 前端直接调用注意事项

如果前端 JS 直调 api-gateway（不通过后端中转）：
1. 在 `api-gateway/.env` 中填写 `CORS_ORIGINS=https://你的前端域名`
2. 重启服务：`nssm restart WikiApiGateway`
3. **强烈不建议**在前端代码中明文存放 API Key，安全做法是通过后端中转

---

## 六、API 速查表

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| `GET` | `/health` | 无 | 健康检查 |
| `GET` | `/docs` | 无 | Swagger 文档 |
| `POST` | `/v1/query` | `query` | 结构化知识查询 |
| `POST` | `/v1/chat` | `chat` | 自由问答 |
| `POST` | `/v1/retrieve` | `query` | 纯检索（不调 LLM 总结） |
| `POST` | `/v1/ingest` | `query` | 摄入文件到知识库 |
| `GET` | `/v1/ingest/{task_id}` | `query` | 查询摄入任务状态 |
| `POST` | `/v1/ingest/{task_id}/commit` | `query` | 确认 pending 任务入库 |
| `GET` | `/v1/ingest/pending/list` | `query` | 列出待校对任务 |
| `GET` | `/v1/wiki/options` | `wiki` | 知识库可用选项 |
| `GET` | `/v1/wiki/stats` | `wiki` | 知识库统计 |
| `GET` | `/v1/wiki/entities` | `wiki` | 实体元数据列表 |
| `GET` | `/v1/apps` | admin | 列出注册应用 |
| `POST` | `/v1/apps` | admin | 注册新应用 |
| `GET` | `/v1/apps/{app_id}` | admin | 获取应用详情 |
| `PATCH` | `/v1/apps/{app_id}` | admin | 更新应用信息 |
| `DELETE` | `/v1/apps/{app_id}` | admin | 停用应用 |
| `GET` | `/v1/apps/{app_id}/keys` | admin | 列出应用 Key |
| `POST` | `/v1/apps/{app_id}/keys` | admin | 创建 API Key |
| `DELETE` | `/v1/apps/{app_id}/keys/{key_id}` | admin | 吊销 API Key |
| `GET` | `/v1/gateway/logs` | admin | 查看访问日志 |

---

## 七、常见问题

**Q：调用返回 401 Unauthorized**
- 检查请求头 `X-API-Key` 是否正确
- 检查应用是否被停用（`is_active: false`）
- 检查 Key 是否被吊销

**Q：调用返回 403 Forbidden**
- 检查应用是否有对应 scope（如调用 `/v1/chat` 需要 `chat` scope）

**Q：调用返回 429 Too Many Requests**
- 触发频率限制，等待后重试（默认 60 次/分钟）

**Q：Ingest 上传大文件失败**
- 检查文件是否超过 50MB
- 检查 nginx `client_max_body_size`（当前 60M）

**Q：前端跨域报错（CORS）**
- 确认 `api-gateway/.env` 中 `CORS_ORIGINS` 填了正确的前端域名（含协议和端口）
- 重启服务：`C:\Tools\nssm\win64\nssm.exe restart WikiApiGateway`

**Q：LLM 调用超时**
- 检查服务器能否访问 `api.moonshot.cn`
- 检查 `.env` 中 API Key 是否正确
- 查看 `/health` 端点的 LLM 连通性状态
