from typing import Optional

from mcp_server.dependencies import build_analytics_service, session_scope
from mcp_server.mcp_instance import mcp
from mcp_server.schemas import (
    KeywordStatsParams,
    RatingTrendParams,
    SentimentRatioParams,
    StatCard,
)


@mcp.tool()
def get_keyword_stats(days: int = 7, top_k: int = 5, source: Optional[str] = None) -> StatCard:
    """
    최근 N일간 리뷰에서 가장 많이 언급된 키워드 상위 K개를 집계한다.
    "요즘 리뷰에서 사람들이 뭐라고 해?" 같은 질문에 사용한다.

    Args:
        days: 최근 며칠간의 리뷰를 볼지 (1~90, 기본 7).
        top_k: 상위 몇 개 키워드를 반환할지 (1~20, 기본 5).
        source: goodreads / kyobo / yes24 중 하나. 생략하면 전체 소스를 합쳐서 집계한다.
    """
    params = KeywordStatsParams(days=days, top_k=top_k, source=source)
    with session_scope() as session:
        service = build_analytics_service(session)
        return service.get_keyword_stats(params)


@mcp.tool()
def get_rating_trend(weeks: int = 4, source: Optional[str] = None) -> StatCard:
    """
    최근 N주간의 주간 평균 별점 추이를 반환한다 ("1주 전", "2주 전" ... 형태).
    "최근 별점이 오르고 있어?" 같은 질문에 사용한다.

    Args:
        weeks: 최근 몇 주간의 추이를 볼지 (1~26, 기본 4).
        source: goodreads / kyobo / yes24 중 하나. 생략하면 전체 소스를 합쳐서 집계한다.
    """
    params = RatingTrendParams(weeks=weeks, source=source)
    with session_scope() as session:
        service = build_analytics_service(session)
        return service.get_rating_trend(params)


@mcp.tool()
def get_sentiment_ratio(days: int = 7, source: Optional[str] = None) -> StatCard:
    """
    최근 N일간 리뷰의 긍정/부정/중립 비율을 집계한다.
    "요즘 반응이 좋아 안 좋아?" 같은 질문에 사용한다.

    Args:
        days: 최근 며칠간의 리뷰를 볼지 (1~90, 기본 7).
        source: goodreads / kyobo / yes24 중 하나. 생략하면 전체 소스를 합쳐서 집계한다.
    """
    params = SentimentRatioParams(days=days, source=source)
    with session_scope() as session:
        service = build_analytics_service(session)
        return service.get_sentiment_ratio(params)
