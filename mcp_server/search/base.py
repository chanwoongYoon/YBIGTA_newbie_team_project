from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from mcp_server.models import Review


class SearchProvider(ABC):
    """
    리뷰 텍스트 검색을 담당하는 인터페이스.

    지금은 MySQL LIKE 검색(SQLSearchProvider)만 구현하지만, 데이터가 많아져
    Elasticsearch/OpenSearch로 교체하더라도 ReviewService와 MCP Tool은
    이 인터페이스만 바라보므로 코드를 다시 작성할 필요가 없다.
    """

    @abstractmethod
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
        raise NotImplementedError
