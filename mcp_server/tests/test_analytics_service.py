from mcp_server.schemas import KeywordStatsParams, RatingTrendParams, SentimentRatioParams


def test_keyword_stats_counts_recent_reviews_only(analytics_service):
    # days=5 -> r1(1일전)/r2(2일전)/r3(3일전)만 포함, r4(9일전)/r5(23일전)는 제외
    card = analytics_service.get_keyword_stats(KeywordStatsParams(days=5, top_k=5))
    assert card.caption.endswith("3건")
    joined_labels = "".join(row.label for row in card.rows)
    assert "힐링" in joined_labels or "따뜻" in joined_labels  # 조사 제거 휴리스틱이 어떻게 잘랐든 관련 토큰은 있어야 함


def test_keyword_stats_wider_window_includes_more_reviews(analytics_service):
    card = analytics_service.get_keyword_stats(KeywordStatsParams(days=30, top_k=5))
    assert card.caption.endswith("5건")


def test_rating_trend_buckets_by_week(analytics_service):
    card = analytics_service.get_rating_trend(RatingTrendParams(weeks=4))
    labels = [row.label for row in card.rows]
    assert "1주 전" in labels  # r1,r2,r3 (1~3일전)가 1주차 버킷에 들어감
    # 4주 범위 밖인 r5(23일전은 4주=28일 이내라 포함, but far bucket)는 존재해도 되고 없어도 됨 - 범위만 검증
    assert all(row.value.endswith("점") for row in card.rows)


def test_rating_trend_respects_weeks_window(analytics_service):
    card = analytics_service.get_rating_trend(RatingTrendParams(weeks=1))
    # 1주 이내(0~6일전)에는 r1,r2,r3만 존재
    assert len(card.rows) == 1
    assert card.rows[0].label == "1주 전"


def test_sentiment_ratio_sums_to_100(analytics_service):
    card = analytics_service.get_sentiment_ratio(SentimentRatioParams(days=30))
    total_pct = sum(float(row.value.rstrip("%")) for row in card.rows)
    assert abs(total_pct - 100.0) < 0.5


def test_sentiment_ratio_empty_window_returns_no_rows(analytics_service):
    card = analytics_service.get_sentiment_ratio(SentimentRatioParams(days=90, source="kyobo"))
    assert card.rows == []
