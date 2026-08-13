import hmac

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp_server.config import MCP_AUTH_TOKEN

# 인증을 요구하지 않는 경로 (로드밸런서/컨테이너 헬스체크용)
_PUBLIC_PATHS = {"/healthz"}


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """
    모든 MCP 요청에 `Authorization: Bearer <MCP_AUTH_TOKEN>` 헤더를 강제한다.
    CORS 설정은 브라우저의 요청 정책일 뿐 서버 인증이 아니므로, 인증은 반드시 이 미들웨어에서 처리한다.
    """

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        if not MCP_AUTH_TOKEN:
            # 토큰이 설정되지 않은 상태로 기동하는 것을 막는다 (운영 환경에서 실수로 인증 없이 열리는 것 방지).
            return JSONResponse({"error": "server misconfigured: MCP_AUTH_TOKEN is not set"}, status_code=500)

        auth_header = request.headers.get("authorization", "")
        expected = f"Bearer {MCP_AUTH_TOKEN}"
        if not hmac.compare_digest(auth_header, expected):
            return JSONResponse({"error": "unauthorized"}, status_code=401)

        return await call_next(request)
