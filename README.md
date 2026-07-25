## 리뷰 데이터 크롤링 — 네이버 지도 (담당: 소연)

### 데이터 소개

| 항목 | 내용 |
|---|---|
| 사이트 | 네이버 지도 - 이태리국시 한남 (https://m.place.naver.com/place/1046469739/review/visitor) |
| 대상 | 이태리국시 한남 (음식점) 방문자 리뷰 |
| 수집 개수 | 545개 |
| 저장 경로 | database/reviews_naver.csv |
| 인코딩 | UTF-8 (BOM) |

**데이터 형식**

| 컬럼 | 타입 | 설명 |
|---|---|---|
| date | str | 방문일 (YYYY-MM-DD) |
| rating | int | 방문자 별점 (1~5점) |
| review | str | 리뷰 본문 |

- 별점이 있는 리뷰만 수집 (네이버는 별점이 선택 입력이라 결측 방지)
- 결측치 없음, 중복 제거 완료

### 실행 환경

네이버 지도는 일반 자동화 브라우저의 리뷰 로딩을 CAPTCHA로 차단하므로, undetected-chromedriver와 가상 디스플레이(xvfb)를 사용한다.

```bash
# 1. 시스템 패키지 (Linux/WSL)
sudo apt install -y xvfb

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 실행 (xvfb-run으로 감싸야 함)
cd review_analysis/crawling
xvfb-run -a python main.py -o ../../database -c naver
```

Chrome 버전이 150이 아니면 naver_map_crawler.py의 version_main=150을 설치된 버전에 맞게 수정하세요.