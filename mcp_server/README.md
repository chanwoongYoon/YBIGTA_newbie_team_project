# MCP Server (담당자 B)

도서 리뷰(`review_db.reviews`, goodreads / kyobo / yes24) 데이터를 LLM Agent가 조회할 수 있도록 노출하는 MCP 서버.
`Browser → Next.js Server → MCP Server → DB` 흐름에서 마지막 두 단계를 담당한다.

DB 스키마는 담당자 A가 만든 `collector/schema.sql`을 그대로 따른다. collector(A)는 `MYSQL_*` 계정(쓰기)으로
`reviews` 테이블에 upsert하고, 이 서버는 `MCP_DB_*` 계정(읽기 전용, `mcp_user`)으로만 조회한다.

## 구조

```
mcp_server/
├── server.py            # ASGI 앱 — 인증 미들웨어 + /healthz + REST shim 라우트 등록, uvicorn 진입점
├── mcp_instance.py       # FastMCP 인스턴스 (정식 MCP 프로토콜, 전역 1개)
├── rest_api.py             # web(Next.js Agent)용 단순 REST 어댑터 (/tools, /tools/{name}/call)
├── auth.py                  # Bearer 토큰 인증 미들웨어
├── config.py                  # 환경변수 로딩
├── db.py / models.py           # SQLAlchemy 엔진 및 reviews 테이블 정의
├── schemas.py                    # Tool 입출력 Pydantic 스키마 + 입력 검증
├── tools/                          # MCP Tool 정의 (얇은 계층, service 호출만 함)
├── services/                         # 비즈니스 로직 (review_service, analytics_service)
├── repositories/                       # DB 접근 (parameterized query만 사용, Raw SQL 금지)
├── search/                               # SearchProvider 인터페이스 (SQL → 추후 Elasticsearch 교체 대비)
└── scripts/                                # 로컬 개발용 스키마 생성 / CSV 시드 스크립트
```

호출 흐름: `Tool → Service → Repository/SearchProvider → DB`

## ⚠️ MCP 프로토콜 + REST, 두 개를 같이 노출하는 이유

이 서버는 두 가지 방식으로 Tool을 노출한다:

1. **`/mcp`** — 정식 MCP 프로토콜(JSON-RPC over Streamable HTTP, 공식 `mcp` SDK). 과제에서 요구하는
   **MCP Inspector로 동작 확인**은 이 엔드포인트로 한다.
2. **`/tools`, `/tools/{name}/call`** — web(Next.js Agent, 담당자 C)의 `lib/mcpClient.ts`가 이미
   이 단순 REST 계약(`GET /tools` → `[{name, description, parameters}]`, `POST /tools/{name}/call`
   body `{"arguments": {...}}` → Tool 결과 JSON)으로 만들어져 있어서, 정식 MCP 프로토콜 대신 이 형태를 기대한다.

Tool 구현(`tools/*.py`)은 하나뿐이고, `rest_api.py`는 같은 함수를 그대로 재사용해서 REST로도 노출할 뿐이다
(`@mcp.tool()`은 원본 함수를 그대로 반환하므로 두 경로가 완전히 같은 로직을 탄다).

## 환경 변수

레포 최상위 `.env`에 다음을 채운다 (`.env.example` 참고):

| 변수 | 설명 |
|---|---|
| `MCP_DB_HOST/PORT/USER/PASSWORD/NAME` | RDS 접속 정보. **`MCP_DB_USER`는 SELECT 전용 계정(mcp_user)** 이어야 한다. `MCP_DB_NAME` 기본값은 `review_db` |
| `MCP_AUTH_TOKEN` | Tool 호출 시 요구하는 Bearer 토큰. 비어 있으면 서버가 기동 시 500을 반환하도록 막아뒀다. web(C)의 `MCP_AUTH_TOKEN`과 반드시 같은 값이어야 한다 |
| `MCP_SERVER_PORT` | 내부 리스닝 포트 (기본 8000). 인터넷에 직접 노출하지 말고 Nginx 등 리버스 프록시 뒤에 둘 것 |
| `MCP_MAX_ROW_LIMIT` / `MCP_DEFAULT_ROW_LIMIT` | 조회 row 상한/기본값 |
| `MCP_QUERY_TIMEOUT_MS` | MySQL 세션 `MAX_EXECUTION_TIME` (ms) |

로컬 개발 중 실제 RDS 없이 테스트하려면 `MCP_DATABASE_URL=sqlite:///./dev.db` 를 지정하면 된다 (SQLAlchemy가 이 값을 우선 사용).

## 로컬 실행

```bash
cd mcp_server
python -m venv .venv && . .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 1) 스키마 생성 (RDS에 reviews 테이블이 아직 없다면 — 보통은 A의 collector/schema.sql로 이미 있음)
python -m mcp_server.scripts.init_schema

# 2) (선택) 기존 database/reviews_*.csv를 시드 데이터로 적재 — 실제 MySQL 필요 (MYSQL_* 환경변수,
#    collector.db의 upsert 로직을 그대로 재사용하므로 collector_user 권한 필요)
python -m mcp_server.scripts.seed_from_csv

# 3) 서버 기동
python -m mcp_server.server   # MCP: http://localhost:8000/mcp , REST: http://localhost:8000/tools
```

## MCP Tool 목록 (7개)

**원자료 조회**

| Tool | 설명 |
|---|---|
| `get_available_sources()` | 존재하는 리뷰 소스 목록 (`["goodreads","kyobo","yes24"]`) — 다른 Tool 호출 전 확인용 |
| `get_latest_reviews(source?, limit=20)` | 최신 리뷰 N개 |
| `search_reviews(keyword?, source?, start_date?, end_date?, min_rating?, max_rating?, limit=20, offset=0)` | 조건 검색 (parameterized query, pagination) |
| `aggregate_reviews(source?, period="day"/"week"/"month", start_date?, end_date?)` | 기간별 리뷰 수 / 평균 평점 집계 |

**통계 카드용 (web의 `AgentPayload` `{title, rows:[{label,value}], caption}` 그대로 반환)**

| Tool | 설명 |
|---|---|
| `get_keyword_stats(days=7, top_k=5, source?)` | 최근 N일 리뷰에서 많이 언급된 키워드 TOP K (형태소 분석기 없이 조사 제거 휴리스틱만 사용 — 정밀하지 않음, 필요 시 `services/analytics_service.py`의 `_extract_keywords`만 교체하면 됨) |
| `get_rating_trend(weeks=4, source?)` | 최근 N주 주간 평균 별점 추이 |
| `get_sentiment_ratio(days=7, source?)` | 최근 N일 긍정/부정/중립 비율 (`sentiment_label` 컬럼 기준) |

Raw SQL을 실행하는 Tool은 의도적으로 제공하지 않는다. 허용 컬럼/필터, row 상한, 쿼리 타임아웃은 `repositories/review_repository.py` 와 `schemas.py`에서 강제한다.

## 동작 확인

**MCP Inspector (정식 프로토콜, 과제 필수 캡처용)**

```bash
npx @modelcontextprotocol/inspector
```

Transport: `Streamable HTTP`, URL: `http://localhost:8000/mcp`, Header: `Authorization: Bearer <MCP_AUTH_TOKEN>` 로 접속 후 `List Tools` → `Call Tool`로 각 Tool이 실제 DB 데이터를 반환하는지 확인한다. (`aws/mcp_tools.png`, `aws/mcp_call.png` 캡처용)

**REST (web 연동 확인용)**

```bash
curl -H "Authorization: Bearer $MCP_AUTH_TOKEN" http://localhost:8000/tools
curl -X POST -H "Authorization: Bearer $MCP_AUTH_TOKEN" -H "Content-Type: application/json" \
  -d '{"arguments":{"days":7}}' http://localhost:8000/tools/get_sentiment_ratio/call
```

## 테스트

```bash
pip install pytest
pytest mcp_server/tests -q
```

리포지토리/서비스/분석(analytics) 계층을 in-memory SQLite로 검증한다 (검색·집계·페이지네이션·키워드/추이/비율 집계·입력 검증 포함).

## Docker

레포 루트를 빌드 컨텍스트로 사용한다 (root `Dockerfile`은 `collector`/`app` 쪽 몫이므로 MCP는 별도 이미지로 분리):

```bash
docker build -f mcp_server/Dockerfile -t mcp-server .
docker run -d --name mcp-server --env-file .env -p 8000:8000 mcp-server
```

EC2에는 이 컨테이너를 `ybigta-vpc` / `ybigta-subnet-public1-ap-northeast-2a` (Public Subnet)에 올리되, `mcp-sg` 보안그룹을 사용하고 8000 포트를 그대로 인터넷에 열지 말고 Nginx 리버스 프록시(80/443)를 통해서만 접근하도록 구성한다.

## web(담당자 C)에게 전달할 값

- `MCP_SERVER_URL` = `https://<EC2 도메인 또는 IP>/mcp` 대신, REST 계약을 쓰므로 **`/tools` 접두사가 되는 origin** (예: `https://mcp.example.com`) — `mcpClient.ts`가 내부적으로 `${MCP_SERVER_URL}/tools` 를 호출한다
- `MCP_AUTH_TOKEN` = 이 서버의 `.env`에 설정한 값과 **동일한 값**

## 보안 체크리스트 (README 최종본 작성 시 참고)

- [x] `MCP_DB_USER`는 read-only 권한만 부여
- [x] Raw SQL 실행 Tool 없음 — 모든 조회는 SQLAlchemy Core 표현식(parameterized)
- [x] row 상한(`MCP_MAX_ROW_LIMIT`) + pagination + query timeout 적용
- [x] 모든 요청(REST 포함)에 `Authorization: Bearer` 필수, 토큰 미설정 시 기동 자체를 막음(오탐 방지)
- [x] `MCP_AUTH_TOKEN` 등 credential은 코드에 하드코딩하지 않고 환경변수로만 관리
- [ ] (배포 시 확인) MCP 내부 포트(8000)를 Security Group에서 외부에 직접 열지 않았는지
