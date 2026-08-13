from typing import List, Optional

from mcp_server.dependencies import build_review_service, session_scope
from mcp_server.mcp_instance import mcp
from mcp_server.schemas import LatestReviewsParams, ReviewOut


@mcp.tool()
def get_latest_reviews(source: Optional[str] = None, limit: int = 20) -> List[ReviewOut]:
    """
    가장 최근에 수집된 도서 리뷰를 최신순으로 반환한다.

    Args:
        source: goodreads / kyobo / yes24 중 하나. 생략하면 전체 소스를 합쳐서 반환한다.
        limit: 반환할 최대 리뷰 수 (1~100, 기본 20).
    """
    params = LatestReviewsParams(source=source, limit=limit)
    with session_scope() as session:
        service = build_review_service(session)
        return service.get_latest(params)
