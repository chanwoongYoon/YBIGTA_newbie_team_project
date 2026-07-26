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