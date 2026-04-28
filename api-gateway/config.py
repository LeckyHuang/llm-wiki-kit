"""
API Gateway 配置
所有配置项均从环境变量读取，通过 .env 文件加载。
"""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ─── Wiki 路径（与 wiki-app 共享同一目录）────────────────────
WIKI_PATH = Path(os.getenv("WIKI_PATH", "../wiki")).expanduser().resolve()
MAX_WIKI_CHARS = int(os.getenv("MAX_WIKI_CHARS", "80000"))
MAX_CHAT_WIKI_CHARS = int(os.getenv("MAX_CHAT_WIKI_CHARS", "40000"))

# ─── LLM 配置 ────────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "moonshot")

PROVIDERS: dict[str, dict] = {
    "moonshot": {
        "api_key_env": "MOONSHOT_API_KEY",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "kimi-k2.6",
    },
    "qwen": {
        "api_key_env": "QWEN_API_KEY",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen3.6-plus",
    },
}

# ─── Gateway 数据库 ───────────────────────────────────────────
GW_DB_PATH = os.getenv("GW_DB_PATH", "./gateway.db")

# ─── 管理员主密钥（保护 App/Key 管理接口）────────────────────
# 若未配置则自动生成并打印到日志（仅供开发调试，生产环境请显式配置）
GATEWAY_ADMIN_KEY = os.getenv("GATEWAY_ADMIN_KEY", "")
if not GATEWAY_ADMIN_KEY:
    GATEWAY_ADMIN_KEY = "gwadmin_" + secrets.token_hex(24)
    import sys
    msg = (
        "\n[api-gateway] WARNING: GATEWAY_ADMIN_KEY not set, using temporary key:\n"
        f"  {GATEWAY_ADMIN_KEY}\n"
        "  Please add it to your .env file.\n"
    )
    sys.stdout.buffer.write(msg.encode("utf-8"))
    sys.stdout.buffer.flush()

# ─── 全局限流默认值 ───────────────────────────────────────────
DEFAULT_RATE_LIMIT = int(os.getenv("DEFAULT_RATE_LIMIT", "60"))   # 次/分钟

# ─── 开发调试万能密钥 ─────────────────────────────────────────
# 设置后可绕过数据库校验，拥有全部权限、不限速。
# 生产环境：不设置此变量（或置空）即自动关闭。
DEV_API_KEY = os.getenv("DEV_API_KEY", "").strip()

# ─── CORS 允许来源 ────────────────────────────────────────────
# 逗号分隔，如：https://ai.company.com,http://192.168.1.100:3000
# 留空则允许所有来源（*），生产环境建议显式配置
_cors_raw = os.getenv("CORS_ORIGINS", "")
CORS_ORIGINS: list[str] = [o.strip() for o in _cors_raw.split(",") if o.strip()] or ["*"]

# ─── Schema 目录（domain-config.xlsx 所在）──────────────────
SCHEMA_DIR = Path(os.getenv("SCHEMA_DIR", "../schema")).expanduser().resolve()
