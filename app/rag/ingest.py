"""data/raw/*.md|*.txt 문서를 조문 단위로 잘라 Qdrant에 저장한다.

실행: uv run python -m app.rag.ingest
"""
import re
import uuid
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import settings
from app.rag.embedder import embed, get_embedder

# "제55조(휴일)", "제18조의2(...)" 같은 조문 시작 지점 또는 "## 제목"에서 자른다
ARTICLE_RE = re.compile(r"(?m)^(?=#*\s*제\d+조(?:의\d+)?\s*[\(（]|##\s)")
MAX_CHARS = 1500


def chunk_document(text: str, source: str) -> list[dict]:
    parts = [p.strip() for p in ARTICLE_RE.split(text) if p.strip()]
    chunks = []
    for part in parts:
        title = part.splitlines()[0].lstrip("# ").strip()[:80]
        # 너무 긴 조문은 문단 기준으로 다시 자른다
        buf = ""
        for para in part.split("\n\n"):
            if len(buf) + len(para) > MAX_CHARS and buf:
                chunks.append({"text": buf.strip(), "source": source, "article": title})
                buf = ""
            buf += para + "\n\n"
        if buf.strip():
            chunks.append({"text": buf.strip(), "source": source, "article": title})
    return chunks


def main() -> None:
    raw = Path(settings.raw_dir)
    files = sorted([*raw.glob("*.md"), *raw.glob("*.txt")])
    files = [f for f in files if f.name.lower() != "readme.md"]
    if not files:
        raise SystemExit(f"{raw} 에 문서가 없습니다. data/raw/README.md 를 참고하세요.")

    chunks = []
    for f in files:
        chunks += chunk_document(f.read_text(encoding="utf-8"), source=f.stem)
    print(f"문서 {len(files)}개 → 청크 {len(chunks)}개")

    vectors = embed([f"{c['article']}\n{c['text']}" for c in chunks])

    client = QdrantClient(path=settings.qdrant_path)
    if client.collection_exists(settings.collection):
        client.delete_collection(settings.collection)
    client.create_collection(
        settings.collection,
        vectors_config=VectorParams(size=get_embedder().get_sentence_embedding_dimension(), distance=Distance.COSINE),
    )
    client.upsert(
        settings.collection,
        points=[PointStruct(id=str(uuid.uuid4()), vector=v, payload=c) for v, c in zip(vectors, chunks)],
    )
    print(f"저장 완료: {settings.qdrant_path} / {settings.collection}")


if __name__ == "__main__":
    main()
