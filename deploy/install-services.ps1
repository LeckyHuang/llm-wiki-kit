# ============================================================
# llm-wiki-kit Windows 服务安装脚本（使用 NSSM）
#
# 前置条件：
#   1. 下载 NSSM：https://nssm.cc/download  解压到 C:\Tools\nssm\
#   2. 已完成 .venv 创建和依赖安装（运行过 start.bat）
#   3. 已配置好 .env 文件
#
# 使用方法：
#   以管理员身份运行 PowerShell，执行：
#   .\install-services.ps1
# ============================================================

# ── 修改这里的路径配置 ─────────────────────────────────────────

# 项目根目录（包含 api-gateway 和 wiki-app-hub 的那一层）
$ProjectRoot = "C:\llm-wiki-kit"

# NSSM 可执行文件路径
$NSSM = "C:\Tools\nssm\win64\nssm.exe"

# 日志目录
$LogDir = "$ProjectRoot\logs"

# ── 以下内容无需修改 ──────────────────────────────────────────

$WikiHubDir    = "$ProjectRoot\wiki-app-hub"
$GatewayDir    = "$ProjectRoot\api-gateway"
$WikiHubExe    = "$WikiHubDir\.venv\Scripts\uvicorn.exe"
$GatewayExe    = "$GatewayDir\.venv\Scripts\uvicorn.exe"

# 校验
if (-not (Test-Path $NSSM)) {
    Write-Error "未找到 NSSM：$NSSM`n请下载 https://nssm.cc/download 并解压到 C:\Tools\nssm\"
    exit 1
}
if (-not (Test-Path $WikiHubExe)) {
    Write-Error "未找到虚拟环境：$WikiHubExe`n请先在 wiki-app-hub 目录运行 start.bat 完成初始化"
    exit 1
}
if (-not (Test-Path $GatewayExe)) {
    Write-Error "未找到虚拟环境：$GatewayExe`n请先在 api-gateway 目录运行 start.bat 完成初始化"
    exit 1
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Write-Host "`n日志目录：$LogDir" -ForegroundColor Cyan

# ─── 安装 Wiki App Hub 服务 ─────────────────────────────────

Write-Host "`n[1/2] 安装 WikiAppHub 服务..." -ForegroundColor Green

# 如果服务已存在，先卸载
$existing = & $NSSM status WikiAppHub 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  服务已存在，先停止并卸载..."
    & $NSSM stop WikiAppHub 2>&1 | Out-Null
    & $NSSM remove WikiAppHub confirm 2>&1 | Out-Null
}

& $NSSM install WikiAppHub $WikiHubExe "app:app --host 127.0.0.1 --port 8000 --workers 1"
& $NSSM set WikiAppHub AppDirectory       $WikiHubDir
& $NSSM set WikiAppHub DisplayName        "Wiki App Hub（知识库管理界面）"
& $NSSM set WikiAppHub Description        "Wiki 知识库内部管理界面和 Ingest 引擎"
& $NSSM set WikiAppHub Start              SERVICE_AUTO_START
& $NSSM set WikiAppHub AppStdout          "$LogDir\wiki-app-hub.log"
& $NSSM set WikiAppHub AppStderr          "$LogDir\wiki-app-hub-error.log"
& $NSSM set WikiAppHub AppRotateFiles     1
& $NSSM set WikiAppHub AppRotateBytes     10485760
& $NSSM set WikiAppHub AppRestartDelay    3000

Write-Host "  WikiAppHub 服务安装完成" -ForegroundColor Green

# ─── 安装 API Gateway 服务 ──────────────────────────────────

Write-Host "`n[2/2] 安装 WikiApiGateway 服务..." -ForegroundColor Green

$existing = & $NSSM status WikiApiGateway 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  服务已存在，先停止并卸载..."
    & $NSSM stop WikiApiGateway 2>&1 | Out-Null
    & $NSSM remove WikiApiGateway confirm 2>&1 | Out-Null
}

& $NSSM install WikiApiGateway $GatewayExe "main:app --host 127.0.0.1 --port 8745 --workers 1"
& $NSSM set WikiApiGateway AppDirectory   $GatewayDir
& $NSSM set WikiApiGateway DisplayName    "Wiki API Gateway（知识库对外接口）"
& $NSSM set WikiApiGateway Description    "Wiki 知识库对外 REST API，供文件库系统和 AI 应用调用"
& $NSSM set WikiApiGateway Start          SERVICE_AUTO_START
& $NSSM set WikiApiGateway AppStdout      "$LogDir\api-gateway.log"
& $NSSM set WikiApiGateway AppStderr      "$LogDir\api-gateway-error.log"
& $NSSM set WikiApiGateway AppRotateFiles 1
& $NSSM set WikiApiGateway AppRotateBytes 10485760
& $NSSM set WikiApiGateway AppRestartDelay 3000

Write-Host "  WikiApiGateway 服务安装完成" -ForegroundColor Green

# ─── 启动服务 ────────────────────────────────────────────────

Write-Host "`n正在启动服务..." -ForegroundColor Cyan
& $NSSM start WikiAppHub
Start-Sleep -Seconds 2
& $NSSM start WikiApiGateway
Start-Sleep -Seconds 2

# ─── 验证状态 ────────────────────────────────────────────────

Write-Host "`n服务状态：" -ForegroundColor Cyan
Write-Host "  WikiAppHub    :" (& $NSSM status WikiAppHub)
Write-Host "  WikiApiGateway:" (& $NSSM status WikiApiGateway)

Write-Host @"

安装完成！验证步骤：
  1. 访问 http://127.0.0.1:8000/api/health   → Wiki App Hub 健康检查
  2. 访问 http://127.0.0.1:8745/health       → API Gateway 健康检查
  3. 访问 http://127.0.0.1:8745/docs         → API 文档

常用服务管理命令（管理员 PowerShell）：
  nssm start   WikiAppHub / WikiApiGateway
  nssm stop    WikiAppHub / WikiApiGateway
  nssm restart WikiAppHub / WikiApiGateway
  nssm status  WikiAppHub / WikiApiGateway
"@ -ForegroundColor White
