import pytest
from pydantic import ValidationError

from mcp_server.schemas import LatestReviewsParams, SearchReviewsParams, AggregateReviewsParams


def test_latest_reviews_params_rejects_unknown_source():
    with pytest.raises(ValidationError):
        LatestReviewsParams(source="unknown_source")


def test_latest_reviews_params_rejects_limit_over_max():
    with pytest.raises(ValidationError):
        LatestReviewsParams(limit=10_000)


def test_search_params_rejects_inverted_date_range():
    with pytest.raises(ValidationError):
        SearchReviewsParams(start_date="2026-02-01", end_date="2026-01-01")


def test_search_params_rejects_inverted_rating_range():
    with pytest.raises(ValidationError):
        SearchReviewsParams(min_rating=4.5, max_rating=2.0)


def test_service_get_latest_returns_review_out(review_service):
    result = review_service.get_latest(LatestReviewsParams(source="kyobo", limit=5))
    assert len(result) == 2
    assert all(r.source == "kyobo" for r in result)


def test_service_search_uses_search_provider(review_service):
    result = review_service.search(SearchReviewsParams(keyword="추천"))
    assert len(result) == 1
    assert result[0].source == "yes24"


def test_service_aggregate_returns_buckets(review_service):
    result = review_service.aggregate(AggregateReviewsParams(period="month"))
    assert len(result) == 3
    assert all(b.review_count > 0 for b in result)


def test_service_get_available_sources(review_service):
    assert set(review_service.get_available_sources()) == {"goodreads", "kyobo", "yes24"}
