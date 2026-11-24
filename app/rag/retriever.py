from functools import lru_cache

from qdrant_client import QdrantClient

from app.config import settings
from app.rag.embedder import embed


@lru_cache
def get_qdrant() -> QdrantClient:
    return QdrantClient(path=settings.qdrant_path)


def search_law(query: str, top_k: int | None = None) -> dict:
    """법령·가이드 문서 검색. 에이전트 도구로도 쓰인다.

    TODO(2일차): BM25 하이브리드 검색 + 리랭커(dragonkue/bge-reranker-v2-m3-ko) 추가
    """
    hits = get_qdrant().query_points(
        settings.collection, query=embed([query])[0], limit=top_k or settings.top_k, with_payload=True
    ).points
    return {
        "results": [
            {"source": h.payload["source"], "article": h.payload["article"], "text": h.payload["text"], "score": round(h.score, 4)}
            for h in hits
        ]
    }


SEARCH_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_law",
        "description": "근로기준법·최저임금법·퇴직급여법 등 법령과 가이드 문서를 검색한다. 법적 근거가 필요한 질문에 사용.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "검색할 내용 (한국어)"}},
            "required": ["query"],
        },
    },
}
