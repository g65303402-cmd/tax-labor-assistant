"""로컬 LLM 클라이언트.

openai 패키지는 '클라이언트 라이브러리'로만 쓴다. base_url이 localhost라서
요청은 외부로 나가지 않는다. Ollama → vLLM 전환 시 LLM_BASE_URL만 바꾸면 된다.
"""
from functools import lru_cache

from openai import OpenAI

from app.config import settings


@lru_cache
def get_client() -> OpenAI:
    return OpenAI(base_url=settings.llm_base_url, api_key="local-no-key")


def chat(messages: list, tools: list | None = None):
    kwargs = dict(model=settings.llm_model, messages=messages, temperature=settings.llm_temperature)
    if tools:
        kwargs["tools"] = tools
    return get_client().chat.completions.create(**kwargs)
