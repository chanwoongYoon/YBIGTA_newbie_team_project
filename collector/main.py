import os
import sys
from datetime import datetime
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from review_analysis.crawling.goodreads_api import fetch_reviews
from collector.db import save_reviews, make_review_key

SOURCE = "goodreads"


def to_sentiment_label(stars: Any) -> str:
    """평점 기준 감성 라벨. 팀 통일 파생변수 sentiment_label 규칙."""
    try:
        s = float(stars)
    except (TypeError, ValueError):
        return "neutral"
    if s >= 4:
        return "positive"
    if s <= 2:
        return "negative"
    return "neutral"


def transform(raw_reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """크롤러 출력(stars, date, review)을 DB 스키마에 맞게 변환한다."""
    rows = []
    for r in raw_reviews:
        review_text = (r.get("review") or "").strip()
        if not review_text:
            continue
        review_date = r.get("date")
        rows.append({
            "source": SOURCE,
            "review_key": make_review_key(SOURCE, review_date, review_text),
            "stars": r.get("stars"),
            "review": review_text,
            "review_date": review_date,
            "sentiment_label": to_sentiment_label(r.get("stars")),
        })
    return rows


def main() -> None:
    started = datetime.now()
    print(f"===== collector 시작 {started:%Y-%m-%d %H:%M:%S} =====")

    raw = fetch_reviews(max_reviews=300)
    print(f"[crawl] {len(raw)}건 수집")

    rows = transform(raw)
    print(f"[transform] {len(rows)}건 변환")

    saved = save_reviews(rows)

    elapsed = (datetime.now() - started).total_seconds()
    print(f"===== collector 종료 저장 {saved}건 / {elapsed:.1f}초 =====")


if __name__ == "__main__":
    main()