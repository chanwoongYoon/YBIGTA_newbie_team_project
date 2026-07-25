"""네이버 지도(m.place.naver.com) 방문자 리뷰 크롤러.

관광지 <경복궁>(place ID: 11571707)의 네이버 지도 방문자 리뷰를 수집한다.
네이버 지도 PC 페이지는 비로그인 상태에서 리뷰 추가 로딩이 불안정하므로,
구조가 단순하고 로딩이 안정적인 모바일 페이지(m.place.naver.com)를 사용한다.
목록 하단의 '더보기' 버튼을 반복 클릭해 리뷰를 누적 로드한 뒤 파싱한다.

수집 항목:
    - date: 방문일 (YYYY-MM-DD)
    - rating: 방문자 평점 (1~5점)
    - review: 리뷰 본문
"""

import os
import re
import time
import random
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from bs4 import BeautifulSoup
import undetected_chromedriver as uc  # type: ignore[import-untyped]
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

from review_analysis.crawling.base_crawler import BaseCrawler
from utils.logger import setup_logger


class NaverMapCrawler(BaseCrawler):
    """네이버 지도 이태리 국시 한남 방문자 리뷰를 수집하는 크롤러.

    Attributes:
        output_dir (str): CSV 파일을 저장할 디렉토리 경로.
        place_id (str): 네이버 지도 장소 고유 ID.
        base_url (str): 방문자 리뷰 모바일 페이지 주소.
        driver (Optional[WebDriver]): Selenium 드라이버.
        reviews (List[Dict[str, Any]]): 수집된 리뷰 목록.
    """

    PLACE_ID: str = "1046469739"
    TARGET_COUNT: int = 550
    MAX_CLICK: int = 400
    SAVE_EVERY: int = 50  # 이만큼 모일 때마다 CSV 중간 저장
    CARD_SELECTOR: str = "li.place_apply_pui"
    MORE_SELECTOR: str = "a.fvwqf"

    def __init__(self, output_dir: str) -> None:
        """크롤러를 초기화한다.

        Args:
            output_dir (str): 결과 CSV를 저장할 디렉토리 경로.
        """
        super().__init__(output_dir)
        self.place_id: str = self.PLACE_ID
        self.base_url: str = (
            f"https://m.place.naver.com/place/{self.place_id}/review/visitor"
        )
        self.driver: Optional[WebDriver] = None
        self.reviews: List[Dict[str, Any]] = []
        self.logger = setup_logger()

    def start_browser(self) -> None:
        """undetected-chromedriver로 브라우저를 실행하고 리뷰 페이지에 접속한다.

        네이버가 일반 자동화 브라우저의 리뷰 추가 로딩을 CAPTCHA로 차단하므로,
        봇 감지를 회피하는 undetected-chromedriver를 사용한다.
        """
        options = uc.ChromeOptions()
        options.add_argument("--lang=ko-KR")
        options.add_argument("--window-size=430,932")
        options.add_argument(
            "user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.0 Mobile/15E148 Safari/604.1"
        )
        self.driver = uc.Chrome(options=options, version_main=150)
        self.driver.set_page_load_timeout(60)
        self.driver.get(self.base_url)
        time.sleep(8)
        self.logger.info("브라우저 실행 및 페이지 접속 완료: %s", self.base_url)

    def close_browser(self) -> None:
        """Selenium 브라우저를 종료한다."""
        if self.driver is not None:
            self.driver.quit()
            self.driver = None
            self.logger.info("브라우저 종료")

    def _load_more(self) -> None:
        """'더보기'를 매우 천천히 클릭하며 리뷰를 로드한다.

        봇 감지를 최대한 피하기 위해 클릭 간격을 길게(4~7초) 두고,
        30개마다 20~35초 휴식한다. SAVE_EVERY 단위로 중간 저장한다.
        """
        assert self.driver is not None
        prev, stall, last_saved = 0, 0, 0

        for i in range(self.MAX_CLICK):
            before = len(self.driver.find_elements(By.CSS_SELECTOR, self.CARD_SELECTOR))

            # 천천히 스크롤 (한 번에 안 내리고 나눠서)
            for frac in (0.5, 0.8, 1.0):
                self.driver.execute_script(
                    f"window.scrollTo(0, document.body.scrollHeight*{frac});"
                )
                time.sleep(random.uniform(1.5, 3.0))

            buttons = self.driver.find_elements(By.CSS_SELECTOR, self.MORE_SELECTOR)
            if buttons:
                button = buttons[-1]
                try:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});", button
                    )
                    time.sleep(random.uniform(10.0, 20.0))
                    self.driver.execute_script("arguments[0].click();", button)
                except Exception as exc:  # noqa: BLE001
                    self.logger.debug("더보기 클릭 실패: %s", exc)

            # 새 콘텐츠 대기 (최대 10초)
            for _ in range(20):
                time.sleep(0.5)
                if len(self.driver.find_elements(By.CSS_SELECTOR, self.CARD_SELECTOR)) > before:
                    break

            # 매 클릭 후 사람처럼 4~7초 쉬기
            time.sleep(random.uniform(3.0, 10.0))

            count = len(self.driver.find_elements(By.CSS_SELECTOR, self.CARD_SELECTOR))

            # 30개마다 길게 휴식 + 중간 저장
            if count - last_saved >= self.SAVE_EVERY:
                self._parse_current()
                self.save_to_database()
                last_saved = count
                rest = random.uniform(20.0, 35.0)
                self.logger.info("중간 저장 %d개, %.0f초 휴식", count, rest)
                time.sleep(rest)

            if count >= self.TARGET_COUNT:
                self.logger.info("목표 %d개 도달 (%d개)", self.TARGET_COUNT, count)
                break

            if count == prev:
                stall += 1
                if stall >= 15:
                    self.logger.info("추가 로딩 중단. 최종 %d개", count)
                    break
            else:
                stall = 0
                self.logger.info("현재 %d개 로드", count)
            prev = count

    def _parse_current(self) -> None:
        """현재 로드된 카드를 파싱해 self.reviews에 반영한다 (중복 자동 제거)."""
        assert self.driver is not None
        soup = BeautifulSoup(self.driver.page_source, "lxml")
        cards = soup.select(self.CARD_SELECTOR)
        collected = []
        for card in cards:
            body = self._parse_body(card)
            rating = self._parse_rating(card)
            if not body or rating is None:
                continue
            collected.append(
                {"date": self._parse_date(card), "rating": rating, "review": body}
            )
        self.reviews = collected

    @staticmethod
    def _parse_rating(card: Any) -> Optional[int]:
        """리뷰 카드에서 별점을 정수로 추출한다.

        Args:
            card: BeautifulSoup으로 파싱한 리뷰 카드 요소.

        Returns:
            Optional[int]: 별점(1~5). 별점이 없으면 None.
        """
        node = card.select_one("div.pui__6abRMf")
        if node is None:
            return None
        text = node.get_text(" ", strip=True).replace("별점", "").replace("점", "")
        match = re.search(r"\d+", text)
        return int(match.group()) if match else None

    @staticmethod
    def _parse_date(card: Any) -> Optional[str]:
        """리뷰 카드에서 방문일을 YYYY-MM-DD 형식으로 추출한다.

        'YYYY년 M월 D일' 형태의 전체 날짜 텍스트를 우선 사용하고,
        없으면 time 태그의 'M.D.요일' 형태를 현재 연도 기준으로 변환한다.

        Args:
            card: BeautifulSoup으로 파싱한 리뷰 카드 요소.

        Returns:
            Optional[str]: 'YYYY-MM-DD' 형식의 날짜. 파싱 실패 시 None.
        """
        for span in card.select("span.pui__gfuUIT"):
            text = span.get_text(" ", strip=True)
            match = re.search(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", text)
            if match:
                year, month, day = (int(g) for g in match.groups())
                return f"{year:04d}-{month:02d}-{day:02d}"

        time_node = card.select_one("time")
        if time_node is not None:
            match = re.search(r"(\d{1,2})\.(\d{1,2})", time_node.get_text(strip=True))
            if match:
                month, day = int(match.group(1)), int(match.group(2))
                year = datetime.now().year
                return f"{year:04d}-{month:02d}-{day:02d}"
        return None

    @staticmethod
    def _parse_body(card: Any) -> str:
        """리뷰 카드에서 본문 텍스트를 추출한다.

        본문 컨테이너의 첫 번째 링크만 사용하여 '더보기' 링크 텍스트를 제외하고,
        <br>로 나뉜 줄을 공백으로 이어 붙인다.

        Args:
            card: BeautifulSoup으로 파싱한 리뷰 카드 요소.

        Returns:
            str: 정제된 리뷰 본문. 본문이 없으면 빈 문자열.
        """
        container = card.select_one("div.pui__vn15t2")
        if container is None:
            return ""
        link = container.find("a")
        if link is None:
            return ""
        return link.get_text(" ", strip=True)

    def scrape_reviews(self) -> None:
        """방문자 리뷰를 로드하고 파싱해 self.reviews에 저장한다."""
        self.start_browser()
        try:
            assert self.driver is not None
            self._load_more()
            self._parse_current()  # 최종 파싱
        finally:
            self.close_browser()
        self.logger.info("리뷰 수집 완료. 총 %d개", len(self.reviews))

    def save_to_database(self) -> None:
        """수집한 리뷰를 CSV 파일로 저장한다.

        중복 리뷰를 제거한 뒤 output_dir 아래에 reviews_naver.csv 로 저장한다.
        """
        if not self.reviews:
            self.logger.warning("저장할 리뷰가 없습니다.")
            return

        os.makedirs(self.output_dir, exist_ok=True)
        output_path = os.path.join(self.output_dir, "reviews_naver.csv")

        df = pd.DataFrame(self.reviews, columns=["date", "rating", "review"])

        # 기존 저장분과 합쳐서 이어받기
        if os.path.exists(output_path):
            old = pd.read_csv(output_path)
            df = pd.concat([old, df], ignore_index=True)

        df = df.drop_duplicates(subset=["date", "review"]).reset_index(drop=True)
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        self.logger.info("CSV 저장: %s (%d행)", output_path, len(df))