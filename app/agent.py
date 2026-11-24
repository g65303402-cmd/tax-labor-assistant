"""도구 호출 에이전트 루프.

1) LLM이 질문을 보고 도구(계산/법령검색)를 고른다
2) 도구를 실행해 결과를 다시 LLM에 넣는다
3) LLM은 결과를 근거로 설명만 한다 (숫자는 도구 결과만 사용)
"""
import json
import time

from app.llm import chat
from app.rag.retriever import SEARCH_TOOL_SCHEMA, search_law
from app.tools.payroll import TOOL_SCHEMAS, run_tool

SYSTEM_PROMPT = """너는 한국 소상공인을 돕는 세무·노무 상담 비서다.

규칙:
- 금액·시간 계산은 절대 직접 하지 말고 반드시 계산 도구를 호출한다.
- 법적 근거가 필요하면 search_law로 검색하고, 답변에 조문(예: 근로기준법 제55조)을 표시한다.
- 상시 근로자 수(5인 미만/이상)에 따라 적용 법이 달라지므로, 모르면 먼저 물어본다.
- 도구 결과에 없는 숫자나 조문을 지어내지 않는다.
- 답변 끝에 "정확한 판단은 노무사·세무사 상담을 권장합니다."를 붙인다.
- 한국어로 간결하게 답한다."""

ALL_TOOLS = TOOL_SCHEMAS + [SEARCH_TOOL_SCHEMA]
MAX_STEPS = 5


def _execute(name: str, raw_args: str) -> dict:
    try:
        args = json.loads(raw_args or "{}")
    except json.JSONDecodeError:
        return {"error": "도구 인자가 올바른 JSON이 아닙니다."}
    if name == "search_law":
        return search_law(**args)
    return run_tool(name, args)


def answer(question: str, history: list | None = None) -> dict:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *(history or []), {"role": "user", "content": question}]
    trace = []
    started = time.perf_counter()

    for _ in range(MAX_STEPS):
        msg = chat(messages, tools=ALL_TOOLS).choices[0].message
        if not msg.tool_calls:
            return {
                "answer": msg.content,
                "tool_calls": trace,
                "latency_ms": int((time.perf_counter() - started) * 1000),
            }
        messages.append(msg.model_dump(exclude_none=True))
        for call in msg.tool_calls:
            result = _execute(call.function.name, call.function.arguments)
            trace.append({"tool": call.function.name, "arguments": call.function.arguments, "result": result})
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, ensure_ascii=False)})

    return {"answer": "질문을 처리하지 못했습니다. 조금 더 구체적으로 질문해 주세요.", "tool_calls": trace, "latency_ms": int((time.perf_counter() - started) * 1000)}
