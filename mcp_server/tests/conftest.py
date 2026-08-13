from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mcp_server.models import Base, Review
from mcp_server.repositories.review_repository import ReviewRepository
from mcp_server.search.sql_search_provider import SQLSearchProvider
from mcp_server.services.analytics_service import AnalyticsService
from mcp_server.services.review_service import ReviewService


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


@pytest.fixture()
def session():
    s = _make_session()
    rows = [
        Review(source="goodreads", review_key="k1", rating=4.5, review_date=date(2026, 1, 5),
               review_text="따뜻한 이야기", sentiment_label="positive"),
        Review(source="goodreads", review_key="k2", rating=3.0, review_date=date(2026, 1, 20),
               review_text="그저 그런 소설", sentiment_label="neutral"),
        Review(source="kyobo", review_key="k3", rating=5.0, review_date=date(2026, 2, 1),
               review_text="감동적인 책", sentiment_label="positive"),
        Review(source="kyobo", review_key="k4", rating=4.0, review_date=date(2026, 2, 15),
               review_text="아이가 좋아함", sentiment_label="positive"),
        Review(source="yes24", review_key="k5", rating=5.0, review_date=date(2026, 2, 20),
               review_text="추천합니다", sentiment_label="positive"),
    ]
    s.add_all(rows)
    s.commit()

    yield s
    s.close()


@pytest.fixture()
def repository(session):
    return ReviewRepository(session)


@pytest.fixture()
def review_service(repository):
    return ReviewService(repository, SQLSearchProvider(repository))


# get_keyword_stats/get_rating_trend/get_sentiment_ratio는 "최근 N일/N주"를 date.today() 기준
# 상대 날짜로 계산하므로, 위 session 픽스처의 고정 날짜(2026-01~02)와는 별도의 DB를 쓴다.
@pytest.fixture()
def analytics_session():
    s = _make_session()
    today = date.today()

    def days_ago(n: int) -> date:
        return today - timedelta(days=n)

    rows = [
        Review(source="goodreads", review_key="r1", rating=5.0, review_date=days_ago(1),
               review_text="독고 이야기가 정말 따뜻하다 감동", sentiment_label="positive"),
        Review(source="goodreads", review_key="r2", rating=4.0, review_date=days_ago(2),
               review_text="편의점 배경의 따뜻한 힐링 소설", sentiment_label="positive"),
        Review(source="goodreads", review_key="r3", rating=2.0, review_date=days_ago(3),
               review_text="기대만큼은 아니었다", sentiment_label="negative"),
        Review(source="goodreads", review_key="r4", rating=4.5, review_date=days_ago(9),
               review_text="독고 캐릭터가 인상적인 힐링 이야기", sentiment_label="positive"),
        Review(source="goodreads", review_key="r5", rating=3.0, review_date=days_ago(23),
               review_text="그럭저럭 볼만한 힐링물", sentiment_label="neutral"),
    ]
    s.add_all(rows)
    s.commit()

    yield s
    s.close()


@pytest.fixture()
def analytics_repository(analytics_session):
    return ReviewRepository(analytics_session)


@pytest.fixture()
def analytics_service(analytics_repository):
    return AnalyticsService(analytics_repository)
