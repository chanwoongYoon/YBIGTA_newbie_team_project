from datetime import date


def test_get_latest_filters_by_source(repository):
    result = repository.get_latest(source="kyobo", limit=10)
    assert len(result) == 2
    assert all(r.source == "kyobo" for r in result)
    # 최신순 정렬
    assert result[0].review_date >= result[1].review_date


def test_get_latest_without_source_returns_all(repository):
    result = repository.get_latest(source=None, limit=10)
    assert len(result) == 5


def test_search_by_keyword(repository):
    result = repository.search(
        keyword="감동", source=None, start_date=None, end_date=None,
        min_rating=None, max_rating=None, limit=10, offset=0,
    )
    assert len(result) == 1
    assert "감동" in result[0].review_text


def test_search_by_date_range(repository):
    result = repository.search(
        keyword=None, source=None,
        start_date=date(2026, 2, 1), end_date=date(2026, 2, 15),
        min_rating=None, max_rating=None, limit=10, offset=0,
    )
    dates = {r.review_date for r in result}
    assert dates == {date(2026, 2, 1), date(2026, 2, 15)}


def test_search_by_rating_range(repository):
    result = repository.search(
        keyword=None, source=None, start_date=None, end_date=None,
        min_rating=4.5, max_rating=5.0, limit=10, offset=0,
    )
    assert all(4.5 <= r.rating <= 5.0 for r in result)
    assert len(result) == 3


def test_search_respects_limit_and_offset(repository):
    page1 = repository.search(
        keyword=None, source=None, start_date=None, end_date=None,
        min_rating=None, max_rating=None, limit=2, offset=0,
    )
    page2 = repository.search(
        keyword=None, source=None, start_date=None, end_date=None,
        min_rating=None, max_rating=None, limit=2, offset=2,
    )
    assert len(page1) == 2
    assert len(page2) == 2
    assert {r.id for r in page1}.isdisjoint({r.id for r in page2})


def test_get_available_sources(repository):
    sources = set(repository.get_available_sources())
    assert sources == {"goodreads", "kyobo", "yes24"}


def test_aggregate_by_month_groups_per_source(repository):
    buckets = repository.aggregate(source=None, period="month", start_date=None, end_date=None)
    by_source = {(b["period_start"], b["source"]) for b in buckets}
    # 2026-01: goodreads 2건, 2026-02: kyobo 2건 + yes24 1건 -> 3개 버킷
    assert len(buckets) == 3
    assert ("goodreads" in {s for _, s in by_source})
