"""
LLM 客户端封装
支持 Moonshot / Qwen，与 wiki-app 保持一致的提供商配置。
"""
import os
import logging

from openai import OpenAI
from fastapi import HTTPException

from config import LLM_PROVIDER, PROVIDERS

logger = logging.getLogger(__name__)

# 默认 system prompt（网关通用版，不含展厅业务特定文案）
_DEFAULT_SYSTEM_TPL = (
    "你是专业知识库助手，基于以下知识库内容回答问题。\n\n"
    "{wiki_content}\n\n"
    "工作原则：\n"
    "- 优先基于知识库内容回答，不编造案例或数据\n"
    "- 知识库无相关信息时，明确说明并给出通用行业建议\n"
    "- 回答结构清晰，使用专业但通俗的语言"
)


def _get_client() -> tuple[OpenAI, str]:
    cfg = PROVIDERS.get(LLM_PROVIDER, PROVIDERS["moonshot"])
    api_key = os.getenv(cfg["api_key_env"])
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail=f"LLM provider '{LLM_PROVIDER}' API key 未配置（{cfg['api_key_env']}）",
        )
    return OpenAI(api_key=api_key, base_url=cfg["base_url"]), cfg["model"]


async def call_llm(
    user_prompt: str,
    wiki_content: str,
    system_extra: str = "",
    temperature: float = 0.3,
    max_tokens: int = 3000,
) -> str:
    """
    调用 LLM，返回生成文本。
    system_extra 可附加额外的系统提示（如接入方自定义指令）。
    """
    system_prompt = _DEFAULT_SYSTEM_TPL.format(wiki_content=wiki_content)
    if system_extra:
        system_prompt += f"\n\n{system_extra}"

    try:
        client, model = _get_client()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("LLM 调用失败")
        raise HTTPException(status_code=502, detail=f"LLM 调用失败：{e}")


async def health_check() -> dict:
    """探测 LLM 连通性"""
    try:
        client, model = _get_client()
        client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5,
        )
        return {"llm_status": "ok", "provider": LLM_PROVIDER, "model": model}
    except HTTPException as e:
        return {"llm_status": "error", "provider": LLM_PROVIDER, "detail": e.detail}
    except Exception as e:
        return {"llm_status": "error", "provider": LLM_PROVIDER, "detail": str(e)}
