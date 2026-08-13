from datetime import date
from typing import List, Optional

from mcp_server.dependencies import build_review_service, session_scope
from mcp_server.mcp_instance import mcp
from mcp_server.schemas import AggregateBucket, AggregateReviewsParams


@mcp.tool()
def aggregate_reviews(
    source: Optional[str] = None,
    period: str = "month",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[AggregateBucket]:
    """
    기간별 리뷰 수와 평균 평점을 집계한다. "최근 한 달 평균과 그 이전 한 달 평균을 비교해줘" 같은
    분석 질문에 사용한다.

    Args:
        source: goodreads / kyobo / yes24 중 하나. 생략하면 소스 전체를 합산한다.
        period: 집계 단위. "day" / "week" / "month" 중 하나 (기본 "month").
        start_date, end_date: 집계 기간 (YYYY-MM-DD, 양끝 포함).
    """
    params = AggregateReviewsParams(source=source, period=period, start_date=start_date, end_date=end_date)
    with session_scope() as session:
        service = build_review_service(session)
        return service.aggregate(params)
