## 👥 팀 소개

같은 콘텐츠(도서 **『불편한 편의점』**)의 리뷰를 서로 다른 플랫폼 3곳에서 수집해,
플랫폼별로 리뷰가 어떻게 다른지 비교 분석하는 YBIGTA 신입기수 5조입니다.
팀원 3명이 각각 다른 리뷰 사이트를 하나씩 맡아 크롤링하고, 이후 텍스트·시계열 분석을 함께 진행합니다.

| 이름 | 학과 | 담당 사이트 |
|------|------|-------------|
| 윤찬웅 | 물리학과 | 교보문고 |
| 김소연 | 도시공학과 / 국어국문학과 | YES24 |
| 김예린 | 국제대학 경제학과 | Goodreads |

## 🙋 팀원 자기소개

### 윤찬웅 (물리학과)
물리학과 3학년 재학 중입니다.
**서버**와 **클라우드** 쪽에 관심이 많아 배포 환경과 **CI/CD** 파이프라인을 직접 굴려보는 걸 좋아합니다.
코드를 짜는 것만큼 그 코드가 안정적으로 돌아가고 자동으로 배포되는 구조를 만드는 데 관심이 있습니다.
이번 프로젝트에서는 **교보문고** 리뷰 크롤러를 맡았습니다.

### 김소연 (도시공학과 / 국어국문학과)

### 김예린 (국제대학 경제학과)

## 리뷰 데이터 크롤링 — YES24 (담당: 소연)

### 데이터 소개

| 항목 | 내용 |
|---|---|
| 사이트 | YES24 - 불편한 편의점 (https://www.yes24.com/product/goods/99308021) |
| 대상 | 도서 <불편한 편의점> 회원리뷰 |
| 수집 개수 | 547개 |
| 저장 경로 | database/reviews_yes24.csv |
| 인코딩 | UTF-8 (BOM) |

**데이터 형식**

| 컬럼 | 타입 | 설명 |
|---|---|---|
| date | str | 리뷰 작성일 (YYYY-MM-DD) |
| rating | int | 회원 평점 (0~10점) |
| review | str | 리뷰 본문 |

- Selenium으로 리뷰 목록(GoodsReviewList)을 PageNumber 단위 URL로 순회하며 수집
- 결측치 없음, 중복 제거 완료

### 실행 방법

```bash
pip install -r requirements.txt

cd review_analysis/crawling
python main.py -o ../../database -c yes24
```


- Selenium으로 각 리뷰 페이지 URL을 순회하며 page_source를 파싱한다. 
- Chrome 브라우저가 필요하며 ChromeDriver는 Selenium Manager가 자동 관리한다.



## 리뷰 데이터 크롤링 — 교보문고 (담당: 찬웅)

### 데이터 소개

| 항목 | 내용 |
|---|---|
| 사이트 | 교보문고 - 불편한 편의점(벚꽃 에디션) (https://product.kyobobook.co.kr/detail/S000001803157) |
| 대상 | 도서 <불편한 편의점(벚꽃 에디션)> Klover 리뷰 |
| 수집 개수 | 500개 |
| 저장 경로 | database/reviews_kyobo.csv |
| 인코딩 | UTF-8 (BOM) |

**데이터 형식**

| 컬럼 | 타입 | 설명 |
|---|---|---|
| stars | float | Klover 별점 (0~4점) |
| date | str | 리뷰 작성일 (YYYY-MM-DD) |
| review | str | 리뷰 본문 |

- 상품 상세페이지의 'Klover 리뷰' 위젯을 열고 페이지 번호 버튼을 순서대로 클릭해 페이지네이션(페이지당 10건)하여 수집
- 별점은 채워진(fill=#4DAC27) 클로버 아이콘 개수로 계산 (아이콘 슬롯은 항상 4개 렌더링되므로 채워진 것만 필터링)
- 별점/날짜/본문이 모두 존재하는 리뷰만 유효 데이터로 채택

### 실행 방법

```bash
pip install -r requirements.txt

cd review_analysis/crawling
python main.py -o ../../database -c kyobo
```

Selenium + Chrome 드라이버가 필요하다.

