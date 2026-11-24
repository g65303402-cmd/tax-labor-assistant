"""에이전트 평가: 도구 선택 정확도 + 답변 내 핵심 수치 포함률 + 지연시간.

실행: uv run python -m eval.run_eval
결과는 eval/results/<모델명>.json 에 저장 → 모델/양자화별 비교표의 원자료가 된다.
"""
import json
import statistics
from pathlib import Path

from app.agent import answer
from app.config import settings

HERE = Path(__file__).parent


def main() -> None:
    cases = [json.loads(line) for line in (HERE / "cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = []
    for c in cases:
        res = answer(c["question"])
        tools = [t["tool"] for t in res["tool_calls"]]
        text = res["answer"] or ""
        normalized = text.replace(" ", "")
        hits = [n for n in c["expected_numbers"] if n.replace(" ", "") in normalized or n.replace(",", "") in normalized]
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
