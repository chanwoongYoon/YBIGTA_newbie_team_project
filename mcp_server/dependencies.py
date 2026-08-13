from contextlib import contextmanager
from typing import Iterator

from mcp_server.db import SessionLocal
from mcp_server.repositories.review_repository import ReviewRepository
from mcp_server.search.sql_search_provider import SQLSearchProvider
from mcp_server.services.analytics_service import AnalyticsService
from mcp_server.services.review_service import ReviewService


@contextmanager
def session_scope() -> Iterator:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def build_review_service(session) -> ReviewService:
    repository = ReviewRepository(session)
    search_provider = SQLSearchProvider(repository)
    return ReviewService(repository, search_provider)


def build_analytics_service(session) -> AnalyticsService:
    return AnalyticsService(ReviewRepository(session))
