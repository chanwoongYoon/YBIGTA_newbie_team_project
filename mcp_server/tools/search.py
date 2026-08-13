from datetime import date
from typing import List, Optional

from mcp_server.dependencies import build_review_service, session_scope
from mcp_server.mcp_instance import mcp
from mcp_server.schemas import ReviewOut, SearchReviewsParams


@mcp.tool()
def search_reviews(
    keyword: Optional[str] = None,
    source: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    min_rating: Optional[float] = None,
    max_rating: Optional[float] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[ReviewOut]:
    """
    조건에 맞는 도서 리뷰를 검색한다. 리뷰 본문 키워드, 소스, 기간, 평점 범위로 필터링할 수 있다.

    Args:
        keyword: 리뷰 본문에서 찾을 키워드 (부분 일치).
        source: goodreads / kyobo / yes24 중 하나.
        start_date, end_date: 조회 기간 (YYYY-MM-DD, 양끝 포함).
        min_rating, max_rating: 평점 범위 (0~5).
        limit: 페이지당 결과 수 (1~100, 기본 20).
        offset: 페이지네이션 offset (다음 페이지 조회 시 사용).
    """
    params = SearchReviewsParams(
        keyword=keyword,
        source=source,
        start_date=start_date,
        end_date=end_date,
        min_rating=min_rating,
        max_rating=max_rating,
        limit=limit,
        offset=offset,
    )
    with session_scope() as session:
        service = build_review_service(session)
        return service.search(params)
