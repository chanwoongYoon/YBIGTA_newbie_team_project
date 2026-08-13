from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from mcp_server.config import ALLOWED_SOURCES, DEFAULT_ROW_LIMIT, MAX_ROW_LIMIT

Source = Literal["goodreads", "kyobo", "yes24"]
AggregatePeriod = Literal["day", "week", "month"]


def _validate_source(value: Optional[str]) -> Optional[str]:
    if value is not None and value not in ALLOWED_SOURCES:
        raise ValueError(f"source must be one of {ALLOWED_SOURCES}")
    return value


class ReviewOut(BaseModel):
    id: int
    source: str
    review_key: str
    rating: Optional[float]
    review_date: Optional[date]
    review_text: Optional[str]
    sentiment_label: Optional[str]  # "positive" / "negative" / "neutral"
    collected_at: datetime

    model_config = {"from_attributes": True}


class LatestReviewsParams(BaseModel):
    source: Optional[Source] = Field(None, description="특정 소스만 조회 (goodreads/kyobo/yes24). 생략 시 전체.")
    limit: int = Field(DEFAULT_ROW_LIMIT, ge=1, le=MAX_ROW_LIMIT, description="반환할 최대 리뷰 수")

    _check_source = field_validator("source")(_validate_source)


class SearchReviewsParams(BaseModel):
    keyword: Optional[str] = Field(None, max_length=100, description="리뷰 본문에서 검색할 키워드")
    source: Optional[Source] = Field(None, description="특정 소스만 조회")
    start_date: Optional[date] = Field(None, description="조회 시작일 (포함)")
    end_date: Optional[date] = Field(None, description="조회 종료일 (포함)")
    min_rating: Optional[float] = Field(None, ge=0, le=5, description="최소 평점(0~5)")
    max_rating: Optional[float] = Field(None, ge=0, le=5, description="최대 평점(0~5)")
    limit: int = Field(DEFAULT_ROW_LIMIT, ge=1, le=MAX_ROW_LIMIT, description="페이지당 결과 수")
    offset: int = Field(0, ge=0, le=100_000, description="페이지네이션 offset")

    _check_source = field_validator("source")(_validate_source)

    @field_validator("end_date")
    @classmethod
    def _check_date_range(cls, end_date, info):
        start_date = info.data.get("start_date")
        if start_date and end_date and end_date < start_date:
            raise ValueError("end_date must not be before start_date")
        return end_date

    @field_validator("max_rating")
    @classmethod
    def _check_rating_range(cls, max_rating, info):
        min_rating = info.data.get("min_rating")
        if min_rating is not None and max_rating is not None and max_rating < min_rating:
            raise ValueError("max_rating must not be less than min_rating")
        return max_rating


class AggregateReviewsParams(BaseModel):
    source: Optional[Source] = Field(None, description="특정 소스만 집계. 생략 시 전체 소스 합산.")
    period: AggregatePeriod = Field("month", description="집계 단위: day/week/month")
    start_date: Optional[date] = Field(None, description="집계 시작일 (포함)")
    end_date: Optional[date] = Field(None, description="집계 종료일 (포함)")

    _check_source = field_validator("source")(_validate_source)

    @field_validator("end_date")
    @classmethod
    def _check_date_range(cls, end_date, info):
        start_date = info.data.get("start_date")
        if start_date and end_date and end_date < start_date:
            raise ValueError("end_date must not be before start_date")
        return end_date


class AggregateBucket(BaseModel):
    period_start: date
    source: Optional[str]
    review_count: int
    avg_rating: float


# --- 통계 카드(web의 AgentPayload: {title, rows:[{label,value}], caption})용 분석 Tool 스키마 ---


class KeywordStatsParams(BaseModel):
    days: int = Field(7, ge=1, le=90, description="최근 며칠간의 리뷰를 대상으로 할지")
    top_k: int = Field(5, ge=1, le=20, description="상위 몇 개 키워드를 반환할지")
    source: Optional[Source] = Field(None, description="특정 소스만 집계. 생략 시 전체.")

    _check_source = field_validator("source")(_validate_source)


class RatingTrendParams(BaseModel):
    weeks: int = Field(4, ge=1, le=26, description="최근 몇 주간의 추이를 볼지")
    source: Optional[Source] = Field(None, description="특정 소스만 집계. 생략 시 전체.")

    _check_source = field_validator("source")(_validate_source)


class SentimentRatioParams(BaseModel):
    days: int = Field(7, ge=1, le=90, description="최근 며칠간의 리뷰를 대상으로 할지")
    source: Optional[Source] = Field(None, description="특정 소스만 집계. 생략 시 전체.")

    _check_source = field_validator("source")(_validate_source)


class StatRow(BaseModel):
    label: str
    value: str


class StatCard(BaseModel):
    title: str
    rows: list[StatRow]
    caption: str
