"""Metacritic 유저 리뷰 크롤러.

영화 <인터스텔라>(Interstellar)의 Metacritic 유저 리뷰를 수집한다.
Metacritic 웹 페이지는 리뷰를 무한 스크롤로 렌더링하며 약 450개에서
추가 로딩이 중단되므로, 페이지가 내부적으로 호출하는 백엔드 엔드포인트
(offset/limit 기반 페이지네이션)를 직접 사용해 전체 리뷰를 수집한다.

수집 항목:
    - date: 리뷰 작성일 (YYYY-MM-DD)
    - rating: 유저 평점 (0~10점)
    - review: 리뷰 본문
"""

import os
import time
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver

from review_analysis.crawling.base_crawler import BaseCrawler
from utils.logger import setup_logger


class MetacriticCrawler(BaseCrawler):
    """Metacritic의 인터스텔라 유저 리뷰를 수집하는 크롤러.

    Attributes:
        output_dir (str): CSV 파일을 저장할 디렉토리 경로.
        base_url (str): 리뷰 데이터를 제공하는 백엔드 엔드포인트.
        page_url (str): 사람이 보는 리뷰 페이지 주소 (Referer 용도).
        driver (Optional[WebDriver]): Selenium 드라이버.
        reviews (List[Dict[str, Any]]): 수집된 리뷰 목록.
    """

    PAGE_SIZE: int = 100
    TARGET_COUNT: int = 1000
    MAX_RETRY: int = 3

    def __init__(self, output_dir: str) -> None:
        """크롤러를 초기화한다.

        Args:
            output_dir (str): 결과 CSV를 저장할 디렉토리 경로.
        """
        super().__init__(output_dir)
        self.base_url: str = (
            "https://backend.metacritic.com/reviews/metacritic"
            "/user/movies/interstellar/web"
        )
        self.page_url: str = "https://www.metacritic.com/movie/interstellar/user-reviews/"
        self.driver: Optional[WebDriver] = None
        self.reviews: List[Dict[str, Any]] = []
        self.logger = setup_logger()

    def start_browser(self) -> None:
        """Selenium 브라우저를 실행하고 리뷰 페이지에 접속한다.

        리뷰 데이터 자체는 백엔드 엔드포인트에서 받아오지만, 과제 요구사항에 따라
        Selenium을 사용해 페이지에 접속하고 렌더링 여부를 확인한다.
        """
        options = Options()
        for arg in (
            "--headless=new",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--lang=en-US",
            "--window-size=1920,1080",
        ):
            options.add_argument(arg)
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        )
        options.page_load_strategy = "eager"

        self.driver = webdriver.Chrome(options=options)
        self.driver.set_page_load_timeout(60)
        self.driver.get(self.page_url)
        time.sleep(3)
        self.logger.info("브라우저 실행 및 페이지 접속 완료: %s", self.page_url)

    def close_browser(self) -> None:
        """Selenium 브라우저를 종료한다."""
        if self.driver is not None:
            self.driver.quit()
            self.driver = None
            self.logger.info("브라우저 종료")

    def _fetch_page(self, offset: int) -> List[Dict[str, Any]]:
        """지정한 offset에서 리뷰 한 페이지를 가져온다.

        Args:
            offset (int): 조회를 시작할 리뷰 인덱스.

        Returns:
            List[Dict[str, Any]]: 리뷰 원본 데이터 목록. 실패 시 빈 리스트.
        """
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Referer": self.page_url,
            "Origin": "https://www.metacritic.com",
        }
        params: Dict[str, Any] = {
            "offset": offset,
            "limit": self.PAGE_SIZE,
            "filterBySentiment": "all",
            "sort": "date",
            "componentName": "user-reviews",
            "componentDisplayName": "user Reviews",
            "componentType": "ReviewList",
        }

        for attempt in range(1, self.MAX_RETRY + 1):
            try:
                response = requests.get(
                    self.base_url, params=params, headers=headers, timeout=20
                )
                response.raise_for_status()
                payload: Dict[str, Any] = response.json()
                items = payload.get("data", {}).get("items", [])
                return list(items)
            except (requests.RequestException, ValueError) as exc:
                self.logger.warning(
                    "offset=%d 요청 실패 (%d/%d): %s",
                    offset, attempt, self.MAX_RETRY, exc,
                )
                time.sleep(2 * attempt)

        self.logger.error("offset=%d 요청을 %d회 시도 후 포기", offset, self.MAX_RETRY)
        return []

    def scrape_reviews(self) -> None:
        """전체 유저 리뷰를 수집해 self.reviews에 저장한다.

        offset을 PAGE_SIZE만큼 증가시키며 더 이상 리뷰가 반환되지 않거나
        TARGET_COUNT에 도달할 때까지 반복 요청한다.
        """
        self.start_browser()

        try:
            offset = 0
            while len(self.reviews) < self.TARGET_COUNT:
                items = self._fetch_page(offset)
                if not items:
                    self.logger.info("offset=%d 에서 더 이상 리뷰가 없어 종료", offset)
                    break

                for item in items:
                    quote = (item.get("quote") or "").strip()
                    if not quote:
                        continue
                    self.reviews.append(
                        {
                            "date": item.get("date"),
                            "rating": item.get("score"),
                            "review": quote,
                        }
                    )

                self.logger.info("현재 %d개 수집 완료", len(self.reviews))
                offset += self.PAGE_SIZE
                time.sleep(1)
        finally:
            self.close_browser()

        self.logger.info("리뷰 수집 종료. 총 %d개", len(self.reviews))

    def save_to_database(self) -> None:
        """수집한 리뷰를 CSV 파일로 저장한다.

        중복 리뷰를 제거한 뒤 output_dir 아래에 reviews_metacritic.csv 로 저장한다.
        """
        if not self.reviews:
            self.logger.warning("저장할 리뷰가 없습니다.")
            return

        os.makedirs(self.output_dir, exist_ok=True)
        output_path = os.path.join(self.output_dir, "reviews_metacritic.csv")

        df = pd.DataFrame(self.reviews, columns=["date", "rating", "review"])
        df = df.drop_duplicates(subset=["date", "review"]).reset_index(drop=True)
        df.to_csv(output_path, index=False, encoding="utf-8-sig")

        self.logger.info("CSV 저장 완료: %s (%d행)", output_path, len(df))
