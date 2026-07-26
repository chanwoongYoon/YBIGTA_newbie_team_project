"""YES24 도서 리뷰 크롤러.

도서 <불편한 편의점>(상품 ID: 99308021)의 YES24 회원리뷰를 수집한다.
YES24 상세 페이지는 리뷰를 별도 모듈(GoodsReviewList)에서 페이지 단위로
제공하므로, 해당 엔드포인트를 PageNumber로 페이지네이션하여 수집한다.

수집 항목:
    - date: 리뷰 작성일 (YYYY-MM-DD)
    - rating: 회원 평점 (1~10점)
    - review: 리뷰 본문
"""

import os
import re
import time
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup, Tag

from review_analysis.crawling.base_crawler import BaseCrawler
from utils.logger import setup_logger


class YES24Crawler(BaseCrawler):
    """YES24 <불편한 편의점> 회원리뷰를 수집하는 크롤러.

    Attributes:
        output_dir (str): CSV 파일을 저장할 디렉토리 경로.
        goods_id (str): YES24 도서 상품 ID.
        base_url (str): 회원리뷰 모듈 엔드포인트.
        reviews (List[Dict[str, Any]]): 수집된 리뷰 목록.
    """

    GOODS_ID: str = "99308021"
    TARGET_COUNT: int = 550
    MAX_PAGE: int = 200

    def __init__(self, output_dir: str) -> None:
        """크롤러를 초기화한다.

        Args:
            output_dir (str): 결과 CSV를 저장할 디렉토리 경로.
        """
        super().__init__(output_dir)
        self.goods_id: str = self.GOODS_ID
        self.base_url: str = (
            "https://www.yes24.com/product/communityModules"
            f"/GoodsReviewList/{self.goods_id}"
        )
        self.reviews: List[Dict[str, Any]] = []
        self.logger = setup_logger()

    def start_browser(self) -> None:
        """requests 세션을 준비한다.

        YES24 리뷰는 정적 요청으로 수집 가능하므로 브라우저 대신
        requests 세션에 헤더를 설정한다.
        """
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
                "Referer": f"https://www.yes24.com/product/goods/{self.goods_id}",
            }
        )
        self.logger.info("requests 세션 준비 완료")

    def _parse_rating(self, card: Tag) -> Optional[int]:
        """리뷰 카드에서 별점을 정수로 추출한다.

        Args:
            card (Tag): 리뷰 카드 요소.

        Returns:
            Optional[int]: 별점(1~10). 없으면 None.
        """
        node = card.select_one("span.total_rating")
        if node is None:
            return None
        match = re.search(r"\d+", node.get_text(strip=True))
        return int(match.group()) if match else None

    def _parse_date(self, card: Tag) -> Optional[str]:
        """리뷰 카드에서 작성일(YYYY-MM-DD)을 추출한다.

        Args:
            card (Tag): 리뷰 카드 요소.

        Returns:
            Optional[str]: 'YYYY-MM-DD' 형식 날짜. 없으면 None.
        """
        node = card.select_one("em.txt_date")
        if node is None:
            return None
        match = re.search(r"\d{4}-\d{2}-\d{2}", node.get_text(strip=True))
        return match.group() if match else None

    def _parse_body(self, card: Tag) -> str:
        """리뷰 카드에서 본문 전체를 추출한다.

        잘린 버전(crop) 대신 원본(origin)의 본문을 우선 사용한다.

        Args:
            card (Tag): 리뷰 카드 요소.

        Returns:
            str: 리뷰 본문. 없으면 빈 문자열.
        """
        origin = card.select_one("div.reviewInfoBot.origin div.review_cont")
        node = origin or card.select_one("div.review_cont")
        if node is None:
            return ""
        return node.get_text(" ", strip=True)

    def scrape_reviews(self) -> None:
        """회원리뷰를 페이지 단위로 수집해 self.reviews에 저장한다."""
        self.start_browser()

        for page in range(1, self.MAX_PAGE + 1):
            if len(self.reviews) >= self.TARGET_COUNT:
                break
            try:
                response = self.session.get(
                    self.base_url, params={"PageNumber": page}, timeout=15
                )
                response.encoding = "utf-8"
                response.raise_for_status()
            except requests.RequestException as exc:
                self.logger.warning("page=%d 요청 실패: %s", page, exc)
                time.sleep(2)
                continue

            soup = BeautifulSoup(response.text, "lxml")
            cards = soup.select("div.reviewInfoGrp")
            if not cards:
                self.logger.info("page=%d 리뷰 없음. 수집 종료", page)
                break

            for card in cards:
                body = self._parse_body(card)
                rating = self._parse_rating(card)
                if not body or rating is None:
                    continue
                self.reviews.append(
                    {
                        "date": self._parse_date(card),
                        "rating": rating,
                        "review": body,
                    }
                )

            self.logger.info("page=%d 완료, 누적 %d개", page, len(self.reviews))
            time.sleep(0.5)

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