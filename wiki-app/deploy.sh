#!/bin/bash
# 服务器端部署脚本
# 用法：在服务器上运行一次即可，后续只需 FTP 上传 wiki/ 目录

set -e

echo "=== 安装依赖 ==="
pip3 install -r requirements.txt

echo "=== 复制环境变量配置 ==="
if [ ! -f .env ]; then
  cp .env.example .env
  echo "请编辑 .env 文件填入 API Key 和 Wiki 路径"
  exit 1
fi

# 若 .env 中没有 SECRET_KEY，自动生成并写入（防止重启失效）
if ! grep -q "^SECRET_KEY=" .env || grep -q "^SECRET_KEY=your_secret_key_here" .env; then
  SK=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  # 移除占位值再追加
  sed -i '/^SECRET_KEY=/d' .env
  echo "SECRET_KEY=${SK}" >> .env
  echo "已自动生成 SECRET_KEY 并写入 .env"
fi

echo "=== 创建必要目录 ==="
mkdir -p estimation-files source-files prompts

echo "=== 启动服务（生产模式） ==="
# 用 nohup 后台运行，日志写入 app.log
nohup uvicorn app:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &
echo "服务已启动，PID: $!"
echo "日志：tail -f app.log"
echo "停止服务：kill \$(lsof -t -i:8000)"
