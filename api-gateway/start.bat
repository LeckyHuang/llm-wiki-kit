@echo off
chcp 65001 > nul
cd /d "%~dp0"

if not exist ".venv" (
    echo [初始化] 正在创建虚拟环境...
    python -m venv .venv
    echo [初始化] 正在安装依赖包...
    .venv\Scripts\pip install --upgrade pip
    .venv\Scripts\pip install -r requirements.txt
    echo [初始化] 依赖安装完成
)

if not exist ".env" (
    echo [错误] 未找到 .env 文件
    echo 请先执行：copy .env.example .env
    echo 然后编辑 .env 文件，填写 GATEWAY_ADMIN_KEY 和 MOONSHOT_API_KEY
    pause
    exit /b 1
)

echo [启动] Wiki API Gateway 正在启动 (端口 8745)...
echo [提示] 访问 http://127.0.0.1:8745/docs 查看 API 文档
echo [提示] 按 Ctrl+C 停止服务
echo.
.venv\Scripts\uvicorn main:app --host 127.0.0.1 --port 8745
pause
