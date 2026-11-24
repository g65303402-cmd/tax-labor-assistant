from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    # 로컬 LLM 서버 (Ollama의 OpenAI 호환 엔드포인트). vLLM으로 바꿔도 URL만 바꾸면 된다.
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = "qwen3.5:9b"
    llm_temperature: float = 0.1

    # 임베딩 (로컬 실행, Hugging Face에서 최초 1회 다운로드)
    embed_model: str = "nlpai-lab/KURE-v1"

    # 벡터 DB: Qdrant 로컬 모드 (Docker 없이 파일로 저장)
    qdrant_path: str = str(ROOT / "storage" / "qdrant")
    collection: str = "labor_law"
    top_k: int = 5

    raw_dir: str = str(ROOT / "data" / "raw")

    # 법제처 Open API 인증키(OC). https://open.law.go.kr 에서 신청
    law_api_oc: str = ""


settings = Settings()
