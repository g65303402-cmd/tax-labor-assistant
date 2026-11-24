# 🧾 사장님 세무·노무 AI 비서

직원 2~5명을 둔 소상공인을 위한 **로컬 LLM 기반** 세무·노무 상담 에이전트.
"주휴수당 얼마야?", "4명인데 연차 줘야 돼?" 같은 질문에 **정확한 계산**과 **법적 근거(조문)**를 함께 답한다.

- 🔒 **외부 API 미사용**: LLM·임베딩 모두 로컬 실행. 급여·인사 데이터가 밖으로 나가지 않음
- 🧮 **계산은 코드로**: LLM은 도구를 고르고 설명만, 금액은 검증된 함수가 계산 (단위 테스트로 보장)
- 📚 **조문 인용 RAG**: 근로기준법·최저임금법·퇴직급여법을 조문 단위로 검색

## 아키텍처

```
사용자 ─▶ Streamlit UI ─▶ FastAPI /chat ─▶ Agent 루프 (최대 5스텝)
                                            │
                       ┌────────────────────┼──────────────────────┐
                       ▼                    ▼                      ▼
              로컬 LLM (Ollama)     계산 도구 (payroll.py)    search_law (RAG)
              qwen3.5:9b 등         주휴·최저임금·4대보험·가산수당   KURE-v1 임베딩 + Qdrant
```

## 기술 스택

| 역할 | 선택 | 이유 |
|---|---|---|
| LLM | Ollama + Qwen 3.5 9B (Q4) | M-시리즈 Mac 24GB에서 임베딩과 동시 구동, 도구 호출 지원 |
| 임베딩 | nlpai-lab/KURE-v1 | BGE-M3 기반 한국어 검색 특화, MIT 라이선스 |
| 벡터 DB | Qdrant (로컬 모드) | Docker 없이 시작, 이후 서버 모드로 코드 변경 없이 전환 |
| API / UI | FastAPI / Streamlit | |
| 배포(예정) | vLLM on Modal (서버리스 GPU) | 사용 시에만 과금 |

## 시작하기 (macOS)

```bash
# 1. 도구 설치 (최초 1회)
curl -LsSf https://astral.sh/uv/install.sh | sh     # Python 패키지 관리자
# Ollama: https://ollama.com/download 에서 macOS 앱 설치 후 실행

# 2. 모델 받기 (약 6GB)
ollama pull qwen3.5:9b        # 태그가 없으면 `ollama list`/ollama.com/library에서 확인 후 .env 수정

# 3. 의존성 설치 + 테스트
cd ~/projects/tax-labor-assistant
cp .env.example .env
uv sync
uv run pytest

# 4. 문서 색인 (최초 실행 시 임베딩 모델 약 2GB 다운로드)
uv run python -m app.rag.ingest

# 5. 실행 (터미널 2개)
uv run uvicorn app.main:app --reload
uv run streamlit run ui/streamlit_app.py

# 6. 평가
uv run python -m eval.run_eval
```

> ⚠️ Qdrant 로컬 모드는 한 프로세스만 폴더를 열 수 있다. `ingest`는 API 서버를 끈 상태에서 실행할 것.

## 평가

`eval/cases.jsonl`의 질문으로 **도구 선택 정확도 / 답변 수치 포함률 / 지연시간(p50)** 을 측정한다.

| 모델 | 양자화 | 도구 정확도 | 수치 포함률 | p50 지연 |
|---|---|---|---|---|
| qwen3.5:9b | Q4 | _측정 예정_ | | |
| gemma4:e4b | Q4 | _측정 예정_ | | |
| + LoRA 튜닝 | Q4 | _측정 예정_ | | |

## 로드맵

- [x] 1일차: 계산 도구 + 단위 테스트, RAG 파이프라인, 에이전트 루프, API/UI 골격
- [ ] 2일차: 법령 원문 수집(법제처 Open API), 하이브리드 검색(BM25) + 한국어 리랭커
- [ ] 3일차: 근로계약서 생성 도구, 5인 미만 여부 되묻기 흐름
- [ ] 4일차: 구조화 출력(guided decoding)으로 도구 호출 안정화, 모델 라우팅
- [ ] 5일차: 평가셋 50개로 확장, 모델·양자화 비교표
- [ ] 6일차: vLLM + Modal 배포, Langfuse 관측
- [ ] 7일차: 문서화, 데모 GIF
- [ ] 이후: 도메인 LoRA 파인튜닝, 세무(부가세·원천세) 도구 확장

## 주의

본 서비스의 답변은 참고용이며 법률 자문이 아니다. 요율·최저임금 등 기준값은 [`app/tools/rates.py`](app/tools/rates.py)에서 관리하며 매년 갱신이 필요하다.
