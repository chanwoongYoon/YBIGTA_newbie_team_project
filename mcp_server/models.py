from sqlalchemy import Column, BigInteger, Integer, String, Float, Date, DateTime, Text, Index, UniqueConstraint, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# MySQL에서는 BIGINT AUTO_INCREMENT, SQLite(로컬 테스트)에서는 INTEGER PRIMARY KEY(rowid) alias로 동작시킨다.
_PkType = BigInteger().with_variant(Integer, "sqlite")


class Review(Base):
    """
    담당자 A가 확정한 실제 스키마 (collector/schema.sql)와 1:1로 맞춘다.
    물리 컬럼명(stars/review)과 파이썬 속성명(rating/review_text)이 다른 것은 의도적이다:
    MCP Tool의 외부 인터페이스 이름(rating, review_text)은 안정적으로 유지하면서,
    DB 컬럼명이 바뀌어도 이 파일만 고치면 되도록 하기 위함.
    """

    __tablename__ = "reviews"

    id = Column(_PkType, primary_key=True, autoincrement=True)
    source = Column(String(20), nullable=False)  # goodreads / yes24 / kyobo
    review_key = Column(String(200), nullable=False)  # 사이트 내 고유 식별값 (source와 합쳐 UNIQUE)
    rating = Column("stars", Float, nullable=True)
    review_text = Column("review", Text, nullable=True)
    review_date = Column(Date, nullable=True)
    sentiment_label = Column(String(20), nullable=True)  # "positive" / "negative" / "neutral"

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    collected_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("source", "review_key", name="uk_source_review"),
        Index("idx_source", "source"),
        Index("idx_review_date", "review_date"),
        Index("idx_collected_at", "collected_at"),
    )
