from datetime import date
from typing import List, Optional

from sqlalchemy import func, literal_column, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from mcp_server.config import QUERY_TIMEOUT_MS
from mcp_server.models import Review


class ReviewRepository:
    """
    reviews 테이블에 대한 유일한 접근 지점.
    - 모든 조건은 SQLAlchemy Core 표현식으로 구성되므로(parameterized query) 문자열 SQL 조립이 없다.
    - Tool/Service는 이 클래스를 통해서만 DB에 접근하고, 직접 Connection이나 SQL을 만들지 않는다.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def _dialect(self) -> str:
        return self.session.bind.dialect.name if self.session.bind is not None else "mysql"

    def _apply_query_timeout(self) -> None:
        # MySQL 8.0+ 세션 단위 실행 시간 제한(비정상적으로 오래 걸리는 Query 방지). 다른 방언은 조용히 무시한다.
        if self._dialect() != "mysql":
            return
        try:
            self.session.execute(text(f"SET SESSION MAX_EXECUTION_TIME={QUERY_TIMEOUT_MS}"))
        except OperationalError:
            pass

    def get_latest(self, source: Optional[str], limit: int) -> List[Review]:
        self._apply_query_timeout()
        stmt = select(Review)
        if source:
            stmt = stmt.where(Review.source == source)
        stmt = stmt.order_by(Review.review_date.desc(), Review.collected_at.desc()).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def search(
        self,
        keyword: Optional[str],
        source: Optional[str],
        start_date: Optional[date],
        end_date: Optional[date],
        min_rating: Optional[float],
        max_rating: Optional[float],
        limit: int,
        offset: int,
    ) -> List[Review]:
        self._apply_query_timeout()
        stmt = select(Review)
        if source:
            stmt = stmt.where(Review.source == source)
        if keyword:
            # LIKE 패턴도 bind parameter로 전달되므로 인젝션 위험이 없다.
            stmt = stmt.where(Review.review_text.like(f"%{keyword}%"))
        if start_date:
            stmt = stmt.where(Review.review_date >= start_date)
        if end_date:
            stmt = stmt.where(Review.review_date <= end_date)
        if min_rating is not None:
            stmt = stmt.where(Review.rating >= min_rating)
        if max_rating is not None:
            stmt = stmt.where(Review.rating <= max_rating)
        stmt = stmt.order_by(Review.review_date.desc()).limit(limit).offset(offset)
        return list(self.session.execute(stmt).scalars().all())

    def aggregate(
        self,
        source: Optional[str],
        period: str,
        start_date: Optional[date],
        end_date: Optional[date],
    ) -> List[dict]:
        self._apply_query_timeout()
        bucket = self._period_bucket_expr(period)

        stmt = select(
            bucket.label("period_start"),
            Review.source.label("source"),
            func.count(Review.id).label("review_count"),
            func.avg(Review.rating).label("avg_rating"),
        )
        if source:
            stmt = stmt.where(Review.source == source)
        if start_date:
            stmt = stmt.where(Review.review_date >= start_date)
        if end_date:
            stmt = stmt.where(Review.review_date <= end_date)
        stmt = stmt.group_by(bucket, Review.source).order_by(bucket)

        rows = self.session.execute(stmt).all()
        return [
            {
                "period_start": row.period_start,
                "source": row.source,
                "review_count": row.review_count,
                "avg_rating": float(row.avg_rating) if row.avg_rating is not None else 0.0,
            }
            for row in rows
        ]

    def _period_bucket_expr(self, period: str):
        # period는 AggregatePeriod Literal("day"|"week"|"month")로 이미 검증된 값만 들어오므로
        # literal_column에 그대로 꽂아도 SQL 인젝션 위험이 없다 (사용자 입력이 문자열로 섞이지 않음).
        if self._dialect() == "mysql":
            if period == "day":
                return func.date(Review.review_date)
            if period == "week":
                return literal_column("DATE_SUB(review_date, INTERVAL WEEKDAY(review_date) DAY)")
            return literal_column("DATE_FORMAT(review_date, '%Y-%m-01')")
        # sqlite 등 로컬 개발/테스트 폴백 (근사치)
        if period == "month":
            return literal_column("date(review_date, 'start of month')")
        return func.date(Review.review_date)

    def get_available_sources(self) -> List[str]:
        self._apply_query_timeout()
        stmt = select(Review.source).distinct()
        return [row[0] for row in self.session.execute(stmt).all()]

    def get_texts_since(self, start_date: date, source: Optional[str], limit: int) -> List[str]:
        """analytics_service의 키워드 집계용 원문 조회."""
        self._apply_query_timeout()
        stmt = select(Review.review_text).where(
            Review.review_date >= start_date, Review.review_text.is_not(None)
        )
        if source:
            stmt = stmt.where(Review.source == source)
        stmt = stmt.limit(limit)
        return [row[0] for row in self.session.execute(stmt).all() if row[0]]

    def get_ratings_since(self, start_date: date, source: Optional[str]) -> List[tuple]:
        """analytics_service의 별점 추이 집계용 (review_date, rating) 목록."""
        self._apply_query_timeout()
        stmt = select(Review.review_date, Review.rating).where(
            Review.review_date >= start_date, Review.rating.is_not(None)
        )
        if source:
            stmt = stmt.where(Review.source == source)
        return [(row[0], row[1]) for row in self.session.execute(stmt).all()]

    def count_by_sentiment(self, start_date: date, source: Optional[str]) -> dict:
        """analytics_service의 감성 비율 집계용."""
        self._apply_query_timeout()
        stmt = (
            select(Review.sentiment_label, func.count(Review.id))
            .where(Review.review_date >= start_date, Review.sentiment_label.is_not(None))
            .group_by(Review.sentiment_label)
        )
        if source:
            stmt = stmt.where(Review.source == source)
        return {label: count for label, count in self.session.execute(stmt).all()}
