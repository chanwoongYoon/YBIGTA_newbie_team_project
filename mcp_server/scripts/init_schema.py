"""
reviews 테이블을 생성한다 (이미 있으면 건드리지 않음).

운영 DB는 담당자 A의 collector/schema.sql로 이미 만들어져 있으므로, 이 스크립트는
실제 RDS 없이 로컬(SQLite 등)에서 MCP 서버를 개발/테스트할 때만 쓴다.

사용법:
    python -m mcp_server.scripts.init_schema
"""
from mcp_server.db import engine
from mcp_server.models import Base


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print(f"reviews table ready on {engine.url.render_as_string(hide_password=True)}")


if __name__ == "__main__":
    main()
