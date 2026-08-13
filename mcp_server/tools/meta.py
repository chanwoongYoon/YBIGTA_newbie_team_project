from typing import List

from mcp_server.dependencies import build_review_service, session_scope
from mcp_server.mcp_instance import mcp


@mcp.tool()
def get_available_sources() -> List[str]:
    """
    현재 DB에 존재하는 리뷰 소스 목록을 반환한다 (예: ["goodreads", "kyobo", "yes24"]).
    다른 Tool을 호출하기 전에 유효한 source 값을 확인하는 용도로 사용한다.
    """
    with session_scope() as session:
        service = build_review_service(session)
        return service.get_available_sources()
