# llm-wiki-kit 部署指南（Windows 服务器）

## 一、系统架构

```
                        ┌─────────────────────────────┐
                        │      Windows 服务器          │
  ┌──────────────┐      │  ┌───────────────────────┐  │
  │ 前端 AI 应用 │─────▶│  │   nginx（反向代理）    │  │
  │（独立域名）  │      │  │  :8080 → wiki-app-hub │  │
  └──────────────┘      │  │  :8081 → api-gateway  │  │
                        │  └───────┬───────────────┘  │
  ┌──────────────┐      │          │                   │
  │ 展项文件库   │─────▶│  ┌───────▼───────────────┐  │
  │ 系统         │      │  │  api-gateway (:8745)   │  │
  └──────────────┘      │  │  对外 REST API         │  │
                        │  │  - /v1/query  查询      │  │
  ┌──────────────┐      │  │  - /v1/chat   聊天      │  │
  │ 内部管理员   │─────▶│  │  - /v1/ingest 摄入      │  │
  │ 浏览器       │      │  └───────┬───────────────┘  │
  └──────────────┘      │          │                   │
                        │  ┌───────▼───────────────┐  │
                        │  │  wiki-app-hub (:8000)  │  │
                        │  │  内部管理界面           │  │
                        │  │  - 知识库浏览/编辑      │  │
                        │  │  - Ingest 工作台        │  │
                        │  │  - Pending 任务审核     │  │
                        │  └───────┬───────────────┘  │
                        │          │                   │
                        │  ┌───────▼───────────────┐  │
                        │  │  wiki/ 共享知识库目录  │  │
                        │  │  （Markdown 文件）     │  │
                        │  └───────────────────────┘  │
                        └─────────────────────────────┘
```

**两个服务通过文件系统共享 `wiki/` 目录。**
- `api-gateway`：对外接口，供文件库系统和 AI 应用调用，有 API Key 认证
- `wiki-app-hub`：内部管理界面，知识库维护、Ingest 工作台，有用户名密码登录

---

## 二、前置准备

在服务器上安装以下软件：

### 1. Python 3.11+
- 下载：https://www.python.org/downloads/
- 安装时勾选 "Add Python to PATH"
- 验证：`python --version`

### 2. nginx for Windows
- 下载：http://nginx.org/en/download.html（Stable version）
- 解压到 `C:\nginx`（不要放有中文或空格的路径）
- 验证：`C:\nginx\nginx.exe -v`

### 3. NSSM（Windows 服务管理器）
- 下载：https://nssm.cc/download
- 解压到 `C:\Tools\nssm\`
- 将 `C:\Tools\nssm\win64` 加入系统 PATH（或使用全路径）

---

## 三、部署目录结构

将整个项目复制到服务器（建议路径）：

```
C:\llm-wiki-kit\
├── api-gateway\        ← 对外 API 服务
├── wiki-app-hub\       ← 内部管理界面
├── wiki\               ← 知识库 Markdown 文件（最重要！）
├── schema\             ← domain-config.xlsx 等配置
├── logs\               ← 自动创建，服务运行日志
└── deploy\             ← 本目录（部署脚本）
```

**重要**：`wiki/`、`schema/` 必须一起复制，两个服务都依赖这两个目录。

---

## 四、安装 Python 依赖

在服务器上打开 **命令提示符（CMD）**，分别进入两个服务目录执行：

```cmd
:: 安装 wiki-app-hub 依赖
cd C:\llm-wiki-kit\wiki-app-hub
python -m venv .venv
.venv\Scripts\pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt

:: 安装 api-gateway 依赖
cd C:\llm-wiki-kit\api-gateway
python -m venv .venv
.venv\Scripts\pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt
```

> **注意**：两个服务使用独立的虚拟环境，互不干扰。

---

## 五、配置环境变量

### 5.1 配置 wiki-app-hub

```cmd
cd C:\llm-wiki-kit\wiki-app-hub
copy .env.example .env
notepad .env
```

必须修改的项：

```env
# LLM API 密钥（月之暗面 / 通义千问 二选一）
MOONSHOT_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# JWT 密钥（重要！生产环境必须设置固定的随机字符串，否则重启后用户被踢出）
# 生成方法（PowerShell）：[System.Web.Security.Membership]::GeneratePassword(48, 8)
SECRET_KEY=your-long-random-secret-string-at-least-32-chars

# CORS：填写前端 AI 应用的域名/IP（多个用逗号分隔）
# 留空则允许所有来源（开发调试可用，生产建议填写）
CORS_ORIGINS=https://ai.yourcompany.com,http://192.168.1.100:3000
```

路径相关（按实际目录调整，如项目不在 C 盘）：

```env
WIKI_PATH=C:/llm-wiki-kit/wiki
SCHEMA_DIR=C:/llm-wiki-kit/schema
INGEST_TMP_DIR=C:/llm-wiki-kit/wiki-app-hub/ingest-tmp
DB_PATH=C:/llm-wiki-kit/wiki-app-hub/data.db
```

### 5.2 配置 api-gateway

```cmd
cd C:\llm-wiki-kit\api-gateway
copy .env.example .env
notepad .env
```

必须修改的项：

```env
# LLM API 密钥（与 wiki-app-hub 可用同一个）
MOONSHOT_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# 管理员主密钥（保护 App/Key 管理接口，自己设一个复杂的随机字符串）
GATEWAY_ADMIN_KEY=gwadmin_your_strong_key_here_change_this

# CORS：填写前端 AI 应用的域名/IP
CORS_ORIGINS=https://ai.yourcompany.com,http://192.168.1.100:3000
```

路径相关：

```env
WIKI_PATH=C:/llm-wiki-kit/wiki
SCHEMA_DIR=C:/llm-wiki-kit/schema
GW_DB_PATH=C:/llm-wiki-kit/api-gateway/gateway.db
```

---

## 六、配置 nginx

```cmd
:: 备份原配置
copy C:\nginx\conf\nginx.conf C:\nginx\conf\nginx.conf.bak

:: 复制我们的配置
copy C:\llm-wiki-kit\deploy\nginx.conf C:\nginx\conf\nginx.conf

:: 验证配置
C:\nginx\nginx.exe -t

:: 若显示 configuration file test is successful，启动 nginx
C:\nginx\nginx.exe
```

**配置说明：**
- 端口 `8080`：Wiki 管理界面（内部访问）
- 端口 `8081`：API Gateway（对外）

如需改端口，编辑 `C:\nginx\conf\nginx.conf`，修改 `listen` 行的数字。

**将 nginx 设为开机自启（以管理员身份运行 PowerShell）：**
```powershell
sc.exe create nginx binPath="C:\nginx\nginx.exe" start=auto
sc.exe start nginx
```

---

## 七、注册 Windows 服务

以**管理员身份**打开 PowerShell，执行：

```powershell
cd C:\llm-wiki-kit\deploy

# 先修改脚本中的 $ProjectRoot 路径，确认无误后执行：
.\install-services.ps1
```

脚本会自动：
1. 安装 `WikiAppHub` 和 `WikiApiGateway` 两个 Windows 服务
2. 设置开机自动启动
3. 配置日志文件到 `C:\llm-wiki-kit\logs\`
4. 启动两个服务

---

## 八、验证部署

服务启动后，验证各组件正常运行：

```powershell
# 1. Wiki App Hub 健康检查
Invoke-RestMethod http://127.0.0.1:8000/api/health

# 2. API Gateway 健康检查
Invoke-RestMethod http://127.0.0.1:8745/health

# 3. 通过 nginx 访问（替换为实际服务器 IP）
Invoke-RestMethod http://服务器IP:8080/api/health
Invoke-RestMethod http://服务器IP:8081/health
```

正常响应示例：
```json
{
  "status": "ok",
  "provider": "moonshot",
  "wiki": { "total_entries": 42 }
}
```

---

## 九、初始化操作（首次部署必做）

### 9.1 修改管理员密码

1. 浏览器访问 `http://服务器IP:8080`
2. 使用 `admin` / `admin` 登录（初始密码为 admin）
3. 进入「管理后台」→「用户管理」→修改 admin 密码

> **安全警告**：初始密码极弱，务必在部署后立即修改！

### 9.2 为 api-gateway 注册第一个外部应用

API Gateway 采用「先注册应用→再申领 Key」的方式管理访问权限。

**注册应用（使用管理员密钥）：**

```bash
curl -X POST http://服务器IP:8081/v1/apps \
  -H "X-Admin-Key: 你的GATEWAY_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "展厅AI前端应用",
    "scopes": ["query", "chat"],
    "rate_limit": 60
  }'
```

返回：`{"id": 1, "name": "展厅AI前端应用", ...}`

**获取 API Key：**

```bash
curl -X POST http://服务器IP:8081/v1/apps/1/keys \
  -H "X-Admin-Key: 你的GATEWAY_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"label": "生产环境Key"}'
```

返回：`{"key": "wk_live_xxxxxxxxxx..."}` ← **仅显示一次，请立即保存！**

---

## 十、对接文件库系统（Ingest）

文件库系统通过 api-gateway 的 `/v1/ingest` 接口将文件推送到知识库。

### 10.1 注册文件库系统应用

```bash
curl -X POST http://服务器IP:8081/v1/apps \
  -H "X-Admin-Key: 你的GATEWAY_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "展项文件库系统",
    "scopes": ["query"],
    "rate_limit": 30
  }'
```

获取 Key（同上步骤）。

### 10.2 半自动模式（推荐）

文件上传后进入人工校对流程，管理员在 wiki-app-hub 界面确认后入库：

```python
import requests

# 上传文件（返回 task_id）
with open("展厅方案.pdf", "rb") as f:
    resp = requests.post(
        "http://服务器IP:8081/v1/ingest",
        headers={"X-API-Key": "wk_live_xxxxxxxx"},
        data={"auto_commit": "false"},
        files={"file": f},
    )
task_id = resp.json()["task_id"]
print(f"任务已创建：{task_id}，等待管理员在 Wiki Hub 界面校对确认")
```

管理员登录 `http://服务器IP:8080`，在「外部待入库」Tab 中看到任务，校对后点击确认。

### 10.3 全自动模式

```python
with open("展厅方案.pdf", "rb") as f:
    resp = requests.post(
        "http://服务器IP:8081/v1/ingest",
        headers={"X-API-Key": "wk_live_xxxxxxxx"},
        data={"auto_commit": "true"},   # 直接写入 wiki，无需人工确认
        files={"file": f},
    )
print(resp.json())  # {"task_id": "...", "status": "committed", ...}
```

---

## 十一、对接前端 AI 应用（Query/Chat）

AI 应用需要知识库上下文时，调用 api-gateway 的查询接口。

### 11.1 结构化查询（返回针对特定场景的知识摘要）

```python
import requests

resp = requests.post(
    "http://服务器IP:8081/v1/query",
    headers={
        "X-API-Key": "wk_live_xxxxxxxx",
        "Content-Type": "application/json"
    },
    json={
        "industry": "文博",
        "hall_type": "历史文化展厅",
        "project_type": "新建",
        "include_competitors": True,
        "include_policies": True,
        "question": "有哪些互动装置可以参考？"
    }
)
context = resp.json()["result"]  # 这就是给 AI 的知识库上下文
```

### 11.2 自由问答

```python
resp = requests.post(
    "http://服务器IP:8081/v1/chat",
    headers={"X-API-Key": "wk_live_xxxxxxxx"},
    json={"message": "展厅声光电技术有哪些最新趋势？"}
)
answer = resp.json()["result"]
```

### 11.3 前端直接调用注意事项

如果前端 JS 直接调用 api-gateway（非通过后端中转），需要：
1. 在 `api-gateway/.env` 中配置 `CORS_ORIGINS=https://你的前端域名`
2. 重启 WikiApiGateway 服务
3. **不建议**在前端 JS 中明文存放 API Key，建议通过自己的后端中转

---

## 十二、日常维护

### 重启服务（PowerShell 管理员）
```powershell
nssm restart WikiAppHub
nssm restart WikiApiGateway
```

### 更新代码后重启
```powershell
# 拉取新代码后（或手动替换文件后）
nssm restart WikiAppHub
nssm restart WikiApiGateway
```

### 查看实时日志
```powershell
# wiki-app-hub 日志
Get-Content C:\llm-wiki-kit\logs\wiki-app-hub.log -Wait -Tail 50

# api-gateway 日志
Get-Content C:\llm-wiki-kit\logs\api-gateway.log -Wait -Tail 50
```

### nginx 重载配置
```cmd
C:\nginx\nginx.exe -s reload
```

### 备份知识库
```powershell
# 打包 wiki 目录（建议每日定时执行）
Compress-Archive -Path C:\llm-wiki-kit\wiki -DestinationPath "C:\backup\wiki-$(Get-Date -Format 'yyyyMMdd').zip"
```

---

## 十三、常见问题

**Q：服务启动后访问不到，提示连接拒绝**
- 检查服务是否启动：`nssm status WikiAppHub`
- 检查端口是否监听：`netstat -ano | findstr "8000 8745 8080 8081"`
- 检查 Windows 防火墙是否放开了对应端口

**Q：wiki-app-hub 启动报 `ingest_engine` 模块找不到**
- 确认项目目录结构正确，`wiki-app-hub/` 和 `api-gateway/` 在同一父目录下
- 检查 `ingest_engine.py` 文件是否存在于 `wiki-app-hub/` 目录

**Q：调用 LLM 超时或报错**
- 检查服务器能否访问 `api.moonshot.cn`（可能需要配置代理）
- 检查 `.env` 中的 API Key 是否正确
- 访问 `/health` 端点，查看 LLM 连通性状态

**Q：Ingest 上传大文件失败**
- nginx 端：检查 `client_max_body_size` 是否足够大（当前设为 60M）
- 应用端：检查 `.env` 中 `MAX_INGEST_FILE_MB` 的值

**Q：前端 AI 应用跨域报错（CORS）**
- 确认 `CORS_ORIGINS` 填写了正确的前端域名（含协议和端口）
- 重启服务后生效：`nssm restart WikiApiGateway`

**Q：重启后所有用户被踢出登录**
- wiki-app-hub 的 `SECRET_KEY` 环境变量未设置固定值
- 编辑 `.env` 文件，设置固定的 `SECRET_KEY`，重启服务
