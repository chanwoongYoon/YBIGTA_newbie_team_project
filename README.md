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
| 수집 개수 | 800개 |
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

### 실행 방법

```bash
pip install -r requirements.txt

cd review_analysis/crawling
python main.py -o ../../database -c kyobo
```

Selenium + Chrome 드라이버가 필요하다.

### 전처리 & Feature Engineering

| 항목 | 내용 |
|---|---|
| 입력 | database/reviews_kyobo.csv |
| 출력 | database/preprocessed_reviews_kyobo.csv |

- 결측치 제거(`dropna`), 별점 4점 만점 → 5점 만점 스케일링, 범위 밖 값 clip(1~5)
- 리뷰 본문 정제(줄바꿈/반복 특수문자/연속 공백 제거) 후 `kiwipiepy`로 형태소 분석 (명사·동사·형용사만 추출)
- 파생변수: `sentiment_label`(별점 4점 이상 → 1), `review_length`(형태소 분석 전 원본 리뷰 글자 수) 등
- `TfidfVectorizer`로 리뷰 텍스트 벡터화 (`max_features=1000`)

```bash
cd review_analysis/preprocessing
python main.py -o ../../database -c reviews_kyobo
```

### 시각화

`preprocessed_reviews_kyobo.csv`를 Tableau로 시각화한 결과 (이미지: `review_analysis/plots/`).

| 긍정/부정 비율 | 리뷰 길이 분포 |
|---|---|
| ![긍정 부정 비율](review_analysis/plots/kyobo_sentiment.png) | ![리뷰 길이 분포](review_analysis/plots/kyobo_review_length.png) |

- 긍정(별점 4점 이상) 비율이 94.1%로 압도적으로 높음
- 리뷰 길이는 대부분 10~30자 사이에 몰려있고, 짧은 한줄평 위주. 일부 100자 이상의 장문 리뷰도 존재하는 롱테일 분포

## 리뷰 데이터 크롤링 — Goodreads (담당: 예린)

### 데이터 소개

| 항목 | 내용 |
|---|---|
| 사이트 | Goodreads - 불편한 편의점 ([https://www.goodreads.com/book/show/58481813/reviews?reviewFilters=eyJhZnRlciI6Ik1UUXdNU3d4TnpNM01ESTFNVGd5TlRZNSJ9]) |
| 대상 | 도서 <불편한 편의점> 리뷰 |
| 수집 개수 | 500개 |
| 저장 경로 | database/reviews_goodreads.csv |
| 인코딩 | UTF-8 (BOM) |

**데이터 형식**

| 컬럼 | 타입 | 설명 |
|---|---|---|
| date | str | 리뷰 작성일 (YYYY-MM-DD) |
| stars | int | 회원 별점 (0~5점) |
| review | str | 리뷰 본문 |

### 코드 동작 방식

**API.py 동작 방식**
1. resourceID(굿리즈 작품 고유 ID)로 지정된 <불편한 편의점> 책의 리뷰를 30개 단위로 요청
2. 응답의 'pageInfo.nextPageToken'을 다음 요청의 'pagination.after'에 넣어 반복 호출
3. 3700+ 총 리뷰에 'MAX_REVIEWS' 상한을 두어 500개를 채우면 수집 종료 / 다음 페이지가 없어도 종료하는 것으로 설정
4. 별점이 없거나 작성일이 없는 리뷰 제외
5. 'createdAt' 타임스탬프를 'YYYY-MM-DD' str 로 변환해 다른 csv 파일과 형식 맞춤
6. 리뷰 본문에 섞인 HTML 태그를 Beautiful Soup으로 제거

**왜 Selenium이 아닌 API 직접 호출인가**
- Selenium으로 리뷰 목록(GoodsReviewList)을 PageNumber 단위 URL로 순회하며 수집하였으나, 30개 수집 후 "show more reviews" 버튼 눌러 다음 페이지로 넘어갈때 봇 감지 -> 실패
- Selenium 코드로는 봇 감지가 되어, 비로그인 상태로 코드를 돌리면 30개가 수집 상한
- 500개+ 수집을 위해서 HTML 구조 확인: Goodreads 프론트엔드는 "show more reviews" 버튼을 누를때 Gr
- aphql API 호출로 다음 페이지를 불러오는 방식
- 다음 페이지로 넘어가는 호출을 코드로 직접한다면, 봇 감지 없이 원하는 만큼 리뷰 수집 가능.

**한계**
- 실제 Goodreads에서 페이지를 넘길때 쓰는 'X-Api-Key' 공개 api key를 코드에 하드 코딩하여, api key 변경시 코드가 작동하지 않을 수 있음
- 실제 api key를 public git에 업로드하는 것은 권장되지 않는다는 걸 인지하고 있으나, 대안책으로 매번 env에서 팀원들/ 과제 검수하는 분들이 api key를 직접 찾는 것도 번거롭고 별로라는 생각이 들었습니다. 

### 실행 방법

```bash
python review_analysis/crawling/goodreads_api.py
```


