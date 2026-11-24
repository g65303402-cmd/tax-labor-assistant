"""FastAPI 서버. 실행: uv run uvicorn app.main:app --reload"""
import httpx
from fastapi import FastAPI
from pydantic import BaseModel

from app import agent
from app.config import settings
from app.tools.payroll import run_tool

app = FastAPI(title="세무·노무 AI 비서", version="0.1.0")


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class ToolRequest(BaseModel):
    arguments: dict


@app.get("/health")
def health():
    ollama_root = settings.llm_base_url.removesuffix("/v1")
    try:
        models = [m["name"] for m in httpx.get(f"{ollama_root}/api/tags", timeout=3).json().get("models", [])]
        return {"status": "ok", "llm_model": settings.llm_model, "model_loaded": settings.llm_model in models}
    except httpx.HTTPError:
        return {"status": "llm_unreachable", "llm_base_url": settings.llm_base_url}


@app.post("/chat")
def chat(req: ChatRequest):
    return agent.answer(req.message, req.history)


@app.post("/tools/{name}")
def call_tool(name: str, req: ToolRequest):
    """LLM 없이 계산 도구만 직접 호출 (디버깅·프론트 계산기용)."""
    return run_tool(name, req.arguments)
