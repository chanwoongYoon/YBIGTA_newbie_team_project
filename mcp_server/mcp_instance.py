from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="ybigta-book-review-mcp",
    instructions=(
        "도서 리뷰(goodreads/kyobo/yes24) 데이터를 조회하는 MCP 서버입니다. "
        "먼저 get_available_sources로 유효한 source 값을 확인한 뒤, "
        "get_latest_reviews / search_reviews / aggregate_reviews 를 사용해 필요한 만큼만 조회하세요. "
        "이 서버는 임의의 SQL을 실행하는 기능을 제공하지 않습니다."
    ),
)
