from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import settings


@lru_cache
def get_embedder() -> SentenceTransformer:
    # Apple Silicon이면 자동으로 mps(GPU) 사용
    return SentenceTransformer(settings.embed_model)


def embed(texts: list[str]) -> list[list[float]]:
    return get_embedder().encode(texts, normalize_embeddings=True, show_progress_bar=len(texts) > 32).tolist()
