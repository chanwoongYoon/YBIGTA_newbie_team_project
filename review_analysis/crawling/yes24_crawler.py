"""YES24 도서 리뷰 크롤러.

도서 <불편한 편의점>(상품 ID: 99308021)의 YES24 전체 리뷰를 수집한다.
YES24 리뷰는 상세 페이지의 별도 모듈(GoodsReviewList)에서 페이지 단위로
제공되며, 각 페이지는 PageNumber 파라미터를 가진 독립 URL로 접근할 수 있다.
Selenium 브라우저로 각 페이지 URL을 순회하며 page_source를 BeautifulSoup으로
파싱한다.

수집 항목:
    - date: 리뷰 작성일 (YYYY-MM-DD)
    - rating: 회원 평점 (0~10점)
    - review: 리뷰 본문
"""

import os
import re
import time
from typing import Any, Dict, List, Optional

import pandas as pd
from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver

from review_analysis.crawling.base_crawler import BaseCrawler
from utils.logger import setup_logger


class YES24Crawler(BaseCrawler):
    """YES24 <불편한 편의점> 전체 리뷰를 수집하는 크롤러.

    Attributes:
        output_dir (str): CSV 파일을 저장할 디렉토리 경로.
        goods_id (str): YES24 도서 상품 ID.
        detail_url (str): 도서 상세 페이지 주소 (세션 확보용).
        review_url (str): 리뷰 목록 모듈 엔드포인트.
        driver (Optional[WebDriver]): Selenium 드라이버.
        reviews (List[Dict[str, Any]]): 수집된 리뷰 목록.
    """

    GOODS_ID: str = "99308021"
    TARGET_COUNT: int = 550
    LAST_PAGE: int = 138

    def __init__(self, output_dir: str) -> None:
        """크롤러를 초기화한다.

        Args:
            output_dir (str): 결과 CSV를 저장할 디렉토리 경로.
        """
        super().__init__(output_dir)
        self.goods_id: str = self.GOODS_ID
        self.detail_url: str = f"https://www.yes24.com/product/goods/{self.goods_id}"
        self.review_url: str = (
            "https://www.yes24.com/Product/communityModules"
            f"/GoodsReviewList/{self.goods_id}"
        )
        self.driver: Optional[WebDriver] = None
        self.reviews: List[Dict[str, Any]] = []
        self.logger = setup_logger()

    def start_browser(self) -> None:
        """Selenium 브라우저를 실행하고 상세 페이지에 접속해 세션을 확보한다."""
        options = Options()
        for arg in (
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--lang=ko-KR",
            "--window-size=1400,1000",
        ):
            options.add_argument(arg)
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        )

        self.driver = webdriver.Chrome(options=options)
        self.driver.set_page_load_timeout(60)
        self.driver.get(self.detail_url)
        time.sleep(3)
        self.logger.info("브라우저 실행 및 상세 페이지 접속 완료")

    def close_browser(self) -> None:
        """Selenium 브라우저를 종료한다."""
        if self.driver is not None:
            self.driver.quit()
            self.driver = None
            self.logger.info("브라우저 종료")

    @staticmethod
    def _parse_rating(card: Tag) -> Optional[int]:
        """리뷰 카드에서 별점을 정수로 추출한다."""
        node = card.select_one("span.total_rating")
        if node is None:
            return None
        match = re.search(r"\d+", node.get_text(strip=True))
        return int(match.group()) if match else None

    @staticmethod
    def _parse_date(card: Tag) -> Optional[str]:
        """리뷰 카드에서 작성일(YYYY-MM-DD)을 추출한다."""
        node = card.select_one("em.txt_date")
        if node is None:
            return None
        match = re.search(r"\d{4}-\d{2}-\d{2}", node.get_text(strip=True))
        return match.group() if match else None

    @staticmethod
    def _parse_body(card: Tag) -> str:
        """리뷰 카드에서 본문 전체를 추출한다 (잘린 버전 대신 원본)."""
        origin = card.select_one("div.reviewInfoBot.origin div.review_cont")
        node = origin or card.select_one("div.review_cont")
        if node is None:
            return ""
        return node.get_text(" ", strip=True)

    def _parse_page(self, page_num: int) -> List[Dict[str, Any]]:
        """지정한 페이지의 리뷰 URL을 열고 리뷰를 파싱한다.

        Args:
            page_num (int): 조회할 페이지 번호.

        Returns:
            List[Dict[str, Any]]: 해당 페이지의 리뷰 목록.
        """
        assert self.driver is not None
        url = (
            f"{self.review_url}?goodsSetYn=N&Sort=2"
            f"&PageNumber={page_num}&Type=All"
        )
        self.driver.get(url)
        time.sleep(0.8)

        soup = BeautifulSoup(self.driver.page_source, "lxml")
        page_reviews: List[Dict[str, Any]] = []
        for card in soup.select("div.reviewInfoGrp"):
            body = self._parse_body(card)
            rating = self._parse_rating(card)
            if not body or rating is None:
                continue
            page_reviews.append(
                {
                    "date": self._parse_date(card),
                    "rating": rating,
                    "review": body,
                }
            )
        return page_reviews

    def scrape_reviews(self) -> None:
        """전체 리뷰를 페이지 단위로 순회하며 self.reviews에 저장한다."""
        self.start_browser()

        try:
            for page in range(1, self.LAST_PAGE + 1):
                if len(self.reviews) >= self.TARGET_COUNT:
                    break
                items = self._parse_page(page)
                if not items:
                    self.logger.info("page=%d 리뷰 없음. 수집 종료", page)
                    break
                self.reviews.extend(items)
                if page % 10 == 0:
                    self.logger.info("page=%d, 누적 %d개", page, len(self.reviews))
        finally:
            self.close_browser()

        self.logger.info("리뷰 수집 완료. 총 %d개", len(self.reviews))

    def save_to_database(self) -> None:
        """수집한 리뷰를 CSV 파일로 저장한다.

        중복 리뷰를 제거한 뒤 output_dir 아래에 reviews_yes24.csv 로 저장한다.
        """
        if not self.reviews:
            self.logger.warning("저장할 리뷰가 없습니다.")
            return

        os.makedirs(self.output_dir, exist_ok=True)
        output_path = os.path.join(self.output_dir, "reviews_yes24.csv")

        df = pd.DataFrame(self.reviews, columns=["date", "rating", "review"])
        df = df.drop_duplicates(subset=["date", "review"]).reset_index(drop=True)
        df.to_csv(output_path, index=False, encoding="utf-8-sig")

        self.logger.info("CSV 저장: %s (%d행)", output_path, len(df))