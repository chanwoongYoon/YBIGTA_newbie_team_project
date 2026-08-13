import re
from collections import Counter
from datetime import date, timedelta
from typing import List, Optional, Tuple

from mcp_server.repositories.review_repository import ReviewRepository
from mcp_server.schemas import (
    KeywordStatsParams,
    RatingTrendParams,
    SentimentRatioParams,
    StatCard,
    StatRow,
)

# 형태소 분석기 없이 쓰는 아주 단순한 한국어 키워드 추출 휴리스틱.
# 2글자 이상 한글/영문 토큰에서 흔한 조사/어미 접미사를 잘라내고, 불용어를 걸러 빈도만 센다.
# 정교한 명사 추출이 필요해지면 이 함수만 kiwipiepy 등으로 교체하면 된다 (호출부는 그대로).
_TOKEN_RE = re.compile(r"[가-힣]{2,}|[A-Za-z]{2,}")
_PARTICLE_SUFFIXES = (
    "이었다", "였다", "했다", "한다", "합니다", "입니다", "이다",
    "에서", "에게", "에는", "으로", "로는", "라고", "라는",
    "까지", "부터", "보다", "이나", "이라", "라도", "마저", "조차", "이라도",
    "은", "는", "이", "가", "을", "를", "의", "에", "도", "만", "과", "와", "로", "고", "서",
)
_STOPWORDS = {
    "정말", "너무", "진짜", "그냥", "그리고", "그런데", "하지만", "그래서",
    "이런", "저런", "그런", "있다", "없다", "같다", "이렇게", "저렇게", "그렇게",
    "있는", "없는", "같은", "이것", "저것", "그것", "정도", "등등",
    "우리", "저는", "제가", "것을", "것은", "것이", "수가", "수도", "위해", "통해",
}

_SENTIMENT_LABEL_KO = {"positive": "긍정", "negative": "부정", "neutral": "중립"}
_SENTIMENT_ORDER = ("positive", "negative", "neutral")


def _strip_particle(token: str) -> str:
    for suf in _PARTICLE_SUFFIXES:
        if len(token) > len(suf) + 1 and token.endswith(suf):
            return token[: -len(suf)]
    return token


def _extract_keywords(texts: List[str], top_k: int) -> List[Tuple[str, int]]:
    counter: Counter = Counter()
    for text in texts:
        for raw in _TOKEN_RE.findall(text):
            token = _strip_particle(raw)
            if len(token) < 2 or token in _STOPWORDS:
                continue
            counter[token] += 1
    return counter.most_common(top_k)


class AnalyticsService:
    """
    web(Next.js Agent)의 통계 카드 UI(title/rows/caption)에 바로 꽂을 수 있는 집계 결과를 만든다.
    get_latest_reviews 등 원자료 조회 Tool과 달리, 여기서는 화면에 보여줄 형태까지 조립해서 반환한다.
    """

    def __init__(self, repository: ReviewRepository) -> None:
        self.repository = repository

    def get_keyword_stats(self, params: KeywordStatsParams) -> StatCard:
        start_date = date.today() - timedelta(days=params.days)
        texts = self.repository.get_texts_since(start_date, params.source, limit=2000)
        keywords = _extract_keywords(texts, params.top_k)

        rows = [StatRow(label=word, value=f"{count}회") for word, count in keywords]
        return StatCard(
            title=f"최근 {params.days}일 리뷰에서 많이 언급된 키워드 TOP {params.top_k}",
            rows=rows,
            caption=f"분석 대상: 최근 {params.days}일 수집 리뷰 {len(texts)}건",
        )

    def get_rating_trend(self, params: RatingTrendParams) -> StatCard:
        today = date.today()
        start_date = today - timedelta(days=params.weeks * 7)
        ratings = self.repository.get_ratings_since(start_date, params.source)

        buckets: dict = {}
        for review_date, rating in ratings:
            days_ago = (today - review_date).days
            week_index = days_ago // 7 + 1
            if 1 <= week_index <= params.weeks:
                buckets.setdefault(week_index, []).append(rating)

        rows = []
        for week_index in range(1, params.weeks + 1):
            values = buckets.get(week_index)
            if not values:
                continue
            avg = sum(values) / len(values)
            rows.append(StatRow(label=f"{week_index}주 전", value=f"{avg:.1f}점"))

        return StatCard(
            title=f"최근 {params.weeks}주 평균 별점 추이",
            rows=rows,
            caption=f"분석 대상: 최근 {params.weeks}주 수집 리뷰 {len(ratings)}건",
        )

    def get_sentiment_ratio(self, params: SentimentRatioParams) -> StatCard:
        start_date = date.today() - timedelta(days=params.days)
        counts = self.repository.count_by_sentiment(start_date, params.source)
        total = sum(counts.values())

        rows = []
        for label in _SENTIMENT_ORDER:
            count = counts.get(label, 0)
            if count == 0:
                continue
            pct = (count / total * 100) if total else 0.0
            rows.append(StatRow(label=_SENTIMENT_LABEL_KO[label], value=f"{pct:.1f}%"))

        return StatCard(
            title="긍정 / 부정 리뷰 비율",
            rows=rows,
            caption=f"분석 대상: 최근 {params.days}일 수집 리뷰 {total}건",
        )
