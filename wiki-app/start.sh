#!/bin/bash
# 本地启动脚本（Mac mini 开发/测试用）
cd "$(dirname "$0")"
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
