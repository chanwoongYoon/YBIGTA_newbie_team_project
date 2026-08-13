from datetime import date
from typing import List, Optional

from mcp_server.models import Review
from mcp_server.repositories.review_repository import ReviewRepository
from mcp_server.search.base import SearchProvider


class SQLSearchProvider(SearchProvider):
    """reviews 테이블에 대한 LIKE 기반 기본 검색 구현체."""

    def __init__(self, repository: ReviewRepository) -> None:
        self.repository = repository

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
        return self.repository.search(
            keyword=keyword,
            source=source,
            start_date=start_date,
            end_date=end_date,
            min_rating=min_rating,
            max_rating=max_rating,
            limit=limit,
            offset=offset,
        )
