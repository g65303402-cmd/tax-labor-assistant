# data/raw

RAG에 넣을 원본 문서(.md, .txt)를 두는 곳입니다. 이 README는 색인되지 않습니다.

- `seed_labor_guide.md`: 바로 실행해 볼 수 있는 요약본 (직접 작성, 원문 대조 필요)
- 법령 원문: `.env`에 `LAW_API_OC`를 넣고 `uv run python -m app.rag.law_fetch` 실행
- 추가하면 좋은 자료: 고용노동부 소상공인 노무관리 가이드, 표준근로계약서, 국세청 원천징수 안내

문서를 추가한 뒤에는 `uv run python -m app.rag.ingest`로 다시 색인합니다.
