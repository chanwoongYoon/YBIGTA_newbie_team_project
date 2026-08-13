from typing import List

from mcp_server.repositories.review_repository import ReviewRepository
from mcp_server.schemas import (
    AggregateBucket,
    AggregateReviewsParams,
    LatestReviewsParams,
    ReviewOut,
    SearchReviewsParams,
)
from mcp_server.search.base import SearchProvider


class ReviewService:
    """
    MCP Tool과 DB 계층 사이의 비즈니스 로직.
    입력 검증은 Pydantic 스키마(schemas.py)에서 1차로 끝나 있고,
    여기서는 조회 결과를 Tool이 반환할 형태로 조립하는 역할만 한다.
    """

    def __init__(self, repository: ReviewRepository, search_provider: SearchProvider) -> None:
        self.repository = repository
        self.search_provider = search_provider

    def get_latest(self, params: LatestReviewsParams) -> List[ReviewOut]:
        reviews = self.repository.get_latest(source=params.source, limit=params.limit)
        return [ReviewOut.model_validate(r) for r in reviews]

    def search(self, params: SearchReviewsParams) -> List[ReviewOut]:
        reviews = self.search_provider.search(
            keyword=params.keyword,
            source=params.source,
            start_date=params.start_date,
            end_date=params.end_date,
            min_rating=params.min_rating,
            max_rating=params.max_rating,
            limit=params.limit,
            offset=params.offset,
        )
        return [ReviewOut.model_validate(r) for r in reviews]

    def aggregate(self, params: AggregateReviewsParams) -> List[AggregateBucket]:
        buckets = self.repository.aggregate(
            source=params.source,
            period=params.period,
            start_date=params.start_date,
            end_date=params.end_date,
        )
        return [AggregateBucket(**b) for b in buckets]

    def get_available_sources(self) -> List[str]:
        return self.repository.get_available_sources()
