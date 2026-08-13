from starlette.responses import PlainTextResponse

from mcp_server import tools  # noqa: F401  (side-effect: registers every @mcp.tool())
from mcp_server.auth import BearerAuthMiddleware
from mcp_server.config import MCP_SERVER_HOST, MCP_SERVER_PORT
from mcp_server.mcp_instance import mcp
from mcp_server.rest_api import call_tool_rest, list_tools_rest


@mcp.custom_route("/healthz", methods=["GET"], include_in_schema=False)
async def healthz(request):
    return PlainTextResponse("ok")


# web(Next.js Agent)이 쓰는 단순 REST 계약. 정식 MCP 프로토콜은 /mcp 에 그대로 남아있다
# (MCP Inspector 등으로 동작 확인은 /mcp 를 사용).
mcp.custom_route("/tools", methods=["GET"])(list_tools_rest)
mcp.custom_route("/tools/{name}/call", methods=["POST"])(call_tool_rest)


def create_app():
    """
    Starlette ASGI 앱을 생성한다. 이 앱은 인터넷에 직접 노출하지 않고,
    앞단의 Reverse Proxy(Nginx 등)를 거쳐 80/443 → 내부 포트로만 전달되어야 한다.
    """
    app = mcp.streamable_http_app()
    app.add_middleware(BearerAuthMiddleware)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=MCP_SERVER_HOST, port=MCP_SERVER_PORT)
