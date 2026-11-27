"""에이전트 평가: 도구 선택 정확도 + 답변 내 핵심 수치 포함률 + 지연시간.

실행: uv run python -m eval.run_eval
결과는 eval/results/<모델명>.json 에 저장 → 모델/양자화별 비교표의 원자료가 된다.
"""
import json
import re
import statistics
from pathlib import Path

from app.agent import answer
from app.config import settings

HERE = Path(__file__).parent

# "1억 2,000만 500" / "215만 6,880" / "215만" 같은 한국어 단위 금액 (공백·쉼표 제거 후 기준)
_KOREAN_AMOUNT = re.compile(r"(?:(\d+)억)?(?:(\d{1,4})만)?(\d{1,4})?")


def _korean_to_digits(m: re.Match) -> str:
    eok, man, rest = m.groups()
    if not (eok or man):  # 억·만 단위가 없으면 원문 그대로
        return m.group(0)
    return str(int(eok or 0) * 10**8 + int(man or 0) * 10**4 + int(rest or 0))


def normalize(text: str) -> str:
    """수치 비교용 정규화: 공백·쉼표 제거, 억/만 단위 금액은 숫자로 풀어 쓴다."""
    compact = text.replace(" ", "").replace(",", "")
    return _KOREAN_AMOUNT.sub(lambda m: _korean_to_digits(m) if m.group(0) else "", compact)


def main() -> None:
    cases = [json.loads(line) for line in (HERE / "cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = []
    for c in cases:
        res = answer(c["question"])
        tools = [t["tool"] for t in res["tool_calls"]]
        text = res["answer"] or ""
        normalized = normalize(text)
        hits = [n for n in c["expected_numbers"] if normalize(n) in normalized]
        rows.append({
            "id": c["id"],
            "tool_ok": c["expected_tool"] in tools,
            "number_recall": len(hits) / len(c["expected_numbers"]),
            "latency_ms": res["latency_ms"],
            "tools": tools,
            "answer": text,
        })
        print(f"[{c['id']}] 도구 {'✅' if rows[-1]['tool_ok'] else '❌'} {tools} | 수치 {len(hits)}/{len(c['expected_numbers'])} | {res['latency_ms']}ms")

    summary = {
        "model": settings.llm_model,
        "tool_accuracy": sum(r["tool_ok"] for r in rows) / len(rows),
        "number_recall": statistics.mean(r["number_recall"] for r in rows),
        "latency_p50_ms": statistics.median(r["latency_ms"] for r in rows),
    }
    print("\n요약:", json.dumps(summary, ensure_ascii=False, indent=2))
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    (out / f"{settings.llm_model.replace(':', '_').replace('/', '_')}.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
