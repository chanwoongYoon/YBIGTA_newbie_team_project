"""
web(Next.js Agent, 담당자 C)의 `lib/mcpClient.ts`가 기대하는 단순 REST 계약을 제공한다.

    GET  /tools                -> [{name, description, parameters}]
    POST /tools/{name}/call    -> 바디 {"arguments": {...}} 를 받아 Tool 결과를 그대로 반환

정식 MCP 프로토콜(JSON-RPC over /mcp, mcp_instance.py + tools/)과는 별개의 얇은 어댑터다.
Tool 구현은 하나만 존재하고(tools/*.py), 여기서는 같은 함수를 재사용해 REST로도 노출할 뿐이다.
"""
from typing import Any, Dict

from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp_server.mcp_instance import mcp
from mcp_server.tools.aggregation import aggregate_reviews
from mcp_server.tools.analytics import get_keyword_stats, get_rating_trend, get_sentiment_ratio
from mcp_server.tools.latest import get_latest_reviews
from mcp_server.tools.meta import get_available_sources
from mcp_server.tools.search import search_reviews

# @mcp.tool()은 원본 함수를 그대로 반환하므로, 여기서 같은 함수 객체를 재사용해도
# 정식 MCP 프로토콜 쪽 동작과 완전히 동일한 로직이 실행된다.
_TOOL_FUNCTIONS = {
    "get_latest_reviews": get_latest_reviews,
    "search_reviews": search_reviews,
    "aggregate_reviews": aggregate_reviews,
    "get_available_sources": get_available_sources,
    "get_keyword_stats": get_keyword_stats,
    "get_rating_trend": get_rating_trend,
    "get_sentiment_ratio": get_sentiment_ratio,
}


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


async def list_tools_rest(request: Request) -> JSONResponse:
    tools = await mcp.list_tools()
    body = [
        {"name": t.name, "description": t.description, "parameters": t.inputSchema}
        for t in tools
        if t.name in _TOOL_FUNCTIONS
    ]
    return JSONResponse(body)


async def call_tool_rest(request: Request) -> JSONResponse:
    name = request.path_params["name"]
    func = _TOOL_FUNCTIONS.get(name)
    if func is None:
        return JSONResponse({"error": f"unknown tool: {name}"}, status_code=404)

    try:
        payload = await request.json()
    except Exception:
        payload = {}
    arguments: Dict[str, Any] = payload.get("arguments") or {}

    try:
        result = func(**arguments)
    except (TypeError, ValueError) as e:
        # 잘못된 인자 이름(TypeError) 또는 Pydantic ValidationError(ValueError의 서브클래스)
        return JSONResponse({"error": str(e)}, status_code=400)

    return JSONResponse(_to_jsonable(result))
