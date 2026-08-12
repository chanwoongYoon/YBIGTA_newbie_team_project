import os
import hashlib
import pymysql
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()


def get_conn():
    """collector_user 계정으로 RDS에 연결한다."""
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        db=os.getenv("MYSQL_DATABASE"),
        charset="utf8mb4",
        connect_timeout=10,
    )


UPSERT_SQL = """
INSERT INTO reviews
    (source, review_key, stars, review, review_date, sentiment_label, collected_at)
VALUES
    (%(source)s, %(review_key)s, %(stars)s, %(review)s,
     %(review_date)s, %(sentiment_label)s, NOW())
ON DUPLICATE KEY UPDATE
    stars           = VALUES(stars),
    review          = VALUES(review),
    sentiment_label = VALUES(sentiment_label),
    collected_at    = NOW()
"""


def make_review_key(source: str, review_date: Any, review: str) -> str:
    """리뷰 원문 해시로 고유키를 만든다. 같은 리뷰는 항상 같은 키가 나온다."""
    raw = f"{source}|{review_date}|{review}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def save_reviews(rows: List[Dict[str, Any]]) -> int:
    """리뷰 리스트를 upsert 한다. 저장된 행 수를 반환."""
    if not rows:
        print("[db] 저장할 데이터가 없습니다.")
        return 0

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.executemany(UPSERT_SQL, rows)
        conn.commit()
        print(f"[db] {len(rows)}건 저장 완료")
        return len(rows)
    finally:
        conn.close()


def show_status() -> None:
    """수집 현황을 출력한다. (data_update.png 캡처용)"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT source, COUNT(*) AS cnt, "
                "MIN(collected_at) AS first_collect, "
                "MAX(collected_at) AS last_collect, "
                "MAX(updated_at) AS last_update "
                "FROM reviews GROUP BY source"
            )
            for row in cur.fetchall():
                print(row)
    finally:
        conn.close()


if __name__ == "__main__":
    show_status()