"""법제처 국가법령정보 Open API로 법령 원문을 받아 data/raw/에 저장한다.

준비: https://open.law.go.kr 에서 Open API 신청 → 발급받은 OC 값을 .env의 LAW_API_OC에 입력
실행: uv run python -m app.rag.law_fetch

※ 이 스크립트는 OC 키 없이 작성되어 실제 응답 구조로 검증되지 않았다.
  첫 실행 때 응답 JSON 구조가 다르면 _articles_to_markdown()을 수정할 것.
"""
from pathlib import Path

import httpx

from app.config import settings

LAWS = ["근로기준법", "근로기준법 시행령", "최저임금법", "근로자퇴직급여 보장법"]
BASE = "https://www.law.go.kr/DRF"


def _find_mst(client: httpx.Client, name: str) -> str:
    r = client.get(f"{BASE}/lawSearch.do", params={"OC": settings.law_api_oc, "target": "law", "type": "JSON", "query": name})
    r.raise_for_status()
    laws = r.json()["LawSearch"]["law"]
    laws = laws if isinstance(laws, list) else [laws]
    exact = [law for law in laws if law["법령명한글"] == name]
    return (exact or laws)[0]["법령일련번호"]


def _articles_to_markdown(name: str, data: dict) -> str:
    lines = [f"# {name}\n"]
    for art in data["법령"]["조문"]["조문단위"]:
        if art.get("조문여부") != "조문":
            continue
        lines.append(art["조문내용"].strip())
        for hang in _as_list(art.get("항")):
            lines.append(str(hang.get("항내용", "")).strip())
            for ho in _as_list(hang.get("호")):
                lines.append("  " + str(ho.get("호내용", "")).strip())
        lines.append("")
    return "\n".join(lines)


def _as_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def main() -> None:
    if not settings.law_api_oc:
        raise SystemExit(".env에 LAW_API_OC를 먼저 설정하세요 (https://open.law.go.kr).")
    out = Path(settings.raw_dir)
    with httpx.Client(timeout=30) as client:
        for name in LAWS:
            mst = _find_mst(client, name)
            r = client.get(f"{BASE}/lawService.do", params={"OC": settings.law_api_oc, "target": "law", "MST": mst, "type": "JSON"})
            r.raise_for_status()
            path = out / f"{name.replace(' ', '_')}.md"
            path.write_text(_articles_to_markdown(name, r.json()), encoding="utf-8")
            print(f"저장: {path}")


if __name__ == "__main__":
    main()
