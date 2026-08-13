"""
앞선 과제에서 수집한 database/reviews_*.csv 를 reviews 테이블에 적재하는 로컬 개발용 부트스트랩 스크립트.

실제 운영 데이터는 담당자 A의 collector(goodreads API, 30분 주기)가 채우므로 이 스크립트는
MCP Tool을 실제와 같은 스키마의 데이터로 미리 개발/검증하기 위한 용도로만 쓴다.
collector.db의 upsert 로직(review_key 생성 포함)을 그대로 재사용해서 실제 파이프라인과
동일한 규칙으로 저장되게 한다 — 그래서 collector_user 권한의 MySQL 접속 정보(MYSQL_*)가 필요하다.

사용법 (레포 루트에서):
    python -m mcp_server.scripts.seed_from_csv
"""
import csv
import os
import sys
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from collector.db import make_review_key, save_reviews  # noqa: E402
from collector.main import to_sentiment_label  # noqa: E402

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "database")

# (파일명, 소스명, 평점 컬럼, 평점 스케일 분모) — yes24는 10점 만점이라 5점 만점으로 정규화한다.
SOURCES = [
    ("reviews_goodreads_ko.csv", "goodreads", "stars", 5.0),
    ("reviews_kyobo.csv", "kyobo", "stars", 5.0),
    ("reviews_yes24.csv", "yes24", "rating", 10.0),
]


def _parse_row(row: dict, source: str, rating_col: str, rating_scale: float) -> Optional[dict]:
    date_str = row.get("date") or row.get("review_date")
    text = (row.get("review") or row.get("review_comment") or "").strip()
    rating_raw = row.get(rating_col)
    if not date_str or not text or rating_raw in (None, ""):
        return None
    try:
        review_date = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
        stars = round(float(rating_raw) * (5.0 / rating_scale), 2)
    except (ValueError, TypeError):
        return None
    return {
        "source": source,
        "review_key": make_review_key(source, review_date, text),
        "stars": stars,
        "review": text,
        "review_date": review_date,
        "sentiment_label": to_sentiment_label(stars),
    }


def main() -> None:
    total = 0
    for filename, source, rating_col, scale in SOURCES:
        path = os.path.join(BASE_DIR, filename)
        if not os.path.exists(path):
            print(f"skip (not found): {path}")
            continue
        rows = []
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            for raw_row in csv.DictReader(f):
                parsed = _parse_row(raw_row, source, rating_col, scale)
                if parsed is not None:
                    rows.append(parsed)
        total += save_reviews(rows)
    print(f"seed 완료: 총 {total}건 upsert")


if __name__ == "__main__":
    main()
