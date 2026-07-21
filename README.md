# YBIGTA Newbie Team Project

## 리뷰 데이터 크롤링 (3회차 과제)

### 분석 대상

영화 **인터스텔라 (Interstellar, 2014)** 의 리뷰 데이터를 여러 사이트에서 수집하여 비교 분석한다.

### 데이터 소개 — Metacritic (담당: 소연)

| 항목 | 내용 |
|---|---|
| 사이트 | [Metacritic - Interstellar User Reviews](https://www.metacritic.com/movie/interstellar/user-reviews/) |
| 수집 개수 | 1,000개 |
| 저장 경로 | `database/reviews_metacritic.csv` |
| 인코딩 | UTF-8 (BOM) |

**데이터 형식**

| 컬럼 | 타입 | 설명 | 예시 |
|---|---|---|---|
| `date` | str | 리뷰 작성일 (YYYY-MM-DD) | `2026-07-20` |
| `rating` | int | 유저 평점 (0~10점) | `10` |
| `review` | str | 리뷰 본문 | `Absolut masterpiece! 10/10...` |

- 수집 기간: 2014-11-06 ~ 2026-07-20
- 결측치 없음 (본문이 비어 있는 리뷰는 수집 단계에서 제외)

**수집 방식**

Metacritic 리뷰 페이지는 무한 스크롤로 리뷰를 렌더링하지만 약 450개 지점에서 추가 로딩이 중단된다.
따라서 페이지가 내부적으로 호출하는 백엔드 엔드포인트를 `offset` / `limit` 기반으로 직접 페이지네이션하여
전체 리뷰(총 1,030개 중 1,000개)를 수집했다.

> 최초에는 IMDb와 Rotten Tomatoes를 후보로 검토했으나,
> IMDb는 유저 리뷰가 로그인 게이트로 막혀 있고,
> Rotten Tomatoes는 관객 리뷰 API가 인증 토큰을 요구(HTTP 401)하여 Metacritic으로 선정했다.

### 실행 방법

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 전체 크롤러 실행
cd review_analysis/crawling
python main.py -o ../../database --all

# 3. 특정 크롤러만 실행
python main.py -o ../../database -c metacritic
```

실행 시 Chrome 브라우저가 필요하며, ChromeDriver는 Selenium Manager가 자동으로 관리한다.

| 옵션 | 설명 |
|---|---|
| `-o`, `--output_dir` | CSV 저장 디렉토리 (필수) |
| `-c`, `--crawler` | 실행할 크롤러 선택 |
| `-a`, `--all` | 모든 크롤러 실행 |