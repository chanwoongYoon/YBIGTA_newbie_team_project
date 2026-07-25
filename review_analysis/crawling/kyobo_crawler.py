"""교보문고 도서 리뷰 크롤러.

Selenium으로 상품 상세페이지의 'Klover 리뷰' 섹션을 열고 페이지 번호 버튼을
순서대로 클릭해 리뷰 목록을 페이지네이션(페이지당 10건)한 뒤,
BeautifulSoup으로 page_source를 파싱해 별점/날짜/본문을 추출·저장한다.
"""

from __future__ import annotations

import logging
import os
import random
import time
from typing import Any, Dict, List, Optional

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)

from review_analysis.crawling.base_crawler import BaseCrawler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PAGINATION_UL_SELECTOR = "#kloverReview ul.font-text-s.flex.items-center.gap-2"
REVIEW_LI_SELECTOR = "#kloverReview ul.flex.flex-col > li"


class KyoboCrawler(BaseCrawler):
    """교보문고 '불편한 편의점(벚꽃 에디션)' 상품(saleCmdtid=S000001803157)의 리뷰를 수집한다."""

    SITE_NAME = "kyobo"
    SALE_CMDT_ID = "S000001803157"
    REVIEWS_PER_PAGE = 10
    MAX_PAGES = 500

    def __init__(self, output_dir: str, target_count: int = 500):
        """
        Args:
            output_dir: 크롤링 결과 csv를 저장할 디렉토리 경로 (예: "database")
            target_count: 최종적으로 수집할 리뷰 개수 상한
        """
        super().__init__(output_dir)
        self.base_url = f"https://product.kyobobook.co.kr/detail/{self.SALE_CMDT_ID}"
        self.target_count = target_count
        self.driver: Optional[webdriver.Chrome] = None
        self.results: List[Dict[str, Any]] = []

    def start_browser(self) -> None:
        """Chrome 드라이버를 실행하고 대상 페이지로 이동한다."""
        self.driver = webdriver.Chrome()
        self.driver.get(self.base_url)
        logger.info(f"브라우저 시작 및 페이지 이동: {self.base_url}")

    def _open_review_section(self) -> bool:
        """'리뷰 섹션으로 이동' 버튼을 클릭해 Klover 리뷰 위젯을 로딩한다.

        리뷰 li 태그가 DOM에 붙은 직후에는 날짜/본문 등 내부 콘텐츠가 아직
        비어 있는 경우가 있어, 날짜 요소가 나타날 때까지 한 번 더 대기한다.
        """
        assert self.driver is not None
        try:
            btn = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "klover-review-info"))
            )
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            time.sleep(0.3)
            self.driver.execute_script("arguments[0].click();", btn)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, REVIEW_LI_SELECTOR))
            )
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "p.shrink-0.text-nowrap.text-gray-800")
                )
            )
            time.sleep(0.5)
            return True
        except TimeoutException:
            logger.error("리뷰 섹션을 찾지 못함")
            return False

    def _click_page(self, page_number: int) -> bool:
        """리뷰 목록 페이지네이션에서 page_number 버튼을 클릭한다.

        페이지네이션 숫자 버튼은 PAGINATION_UL_SELECTOR로 범위를 좁혀서 찾는다.
        리뷰 카드마다 있는 '좋아요/댓글' 개수 버튼도 텍스트가 숫자라서,
        범위를 좁히지 않으면 페이지 번호와 혼동될 수 있다.

        Returns:
            버튼을 찾아 클릭했으면 True, 해당 번호 버튼이 없으면(마지막 페이지 초과) False.
        """
        assert self.driver is not None
        buttons = self.driver.find_elements(By.CSS_SELECTOR, f"{PAGINATION_UL_SELECTOR} button")
        target = next((b for b in buttons if b.text.strip() == str(page_number)), None)
        if target is None:
            return False
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target)
            time.sleep(0.2)
            self.driver.execute_script("arguments[0].click();", target)
            time.sleep(random.uniform(1.0, 1.6))
            return True
        except (ElementClickInterceptedException, StaleElementReferenceException):
            return False

    @staticmethod
    def _parse_rating(li: Any) -> Optional[float]:
        """클로버 별점 아이콘(<li> 개수)을 세어 별점을 계산한다."""
        icons = li.select("div.flex.items-center.justify-between ul.flex.items-center > li")
        return float(len(icons)) if icons else None

    @staticmethod
    def _parse_date(li: Any) -> Optional[str]:
        """'YYYY.MM.DD' 형식의 작성일 텍스트를 'YYYY-MM-DD'로 변환한다."""
        date_el = li.select_one("p.shrink-0.text-nowrap.text-gray-800")
        if date_el is None:
            return None
        raw = date_el.get_text(strip=True)
        parts = raw.split(".")
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            y, m, d = parts
            return f"{y}-{int(m):02d}-{int(d):02d}"
        return raw or None

    @staticmethod
    def _parse_review_text(li: Any) -> str:
        """본문 문단(line-clamp-3, CSS 상 3줄로만 보이지만 DOM에는 전체 텍스트가 존재)을 추출한다."""
        text_el = li.select_one("p.line-clamp-3")
        if text_el is None:
            return ""
        return text_el.get_text(strip=True)

    def _parse_current_page(self) -> List[Dict[str, Any]]:
        """현재 page_source에서 리뷰 목록(최대 10건)을 파싱한다."""
        assert self.driver is not None
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        lis = soup.select(REVIEW_LI_SELECTOR)

        parsed: List[Dict[str, Any]] = []
        for li in lis:
            parsed.append({
                "stars": self._parse_rating(li),
                "date": self._parse_date(li),
                "review": self._parse_review_text(li),
            })
        return parsed

    def scrape_reviews(self) -> List[Dict[str, Any]]:
        """target_count개를 모으거나 더 이상 페이지가 없을 때까지 리뷰를 수집한다.

        Returns:
            {"stars": float | None, "date": str | None, "review": str} 딕셔너리 리스트
        """
        self.start_browser()
        assert self.driver is not None

        if not self._open_review_section():
            self.driver.quit()
            return []

        def is_valid(r: Dict[str, Any]) -> bool:
            return r["stars"] is not None and r["date"] and r["review"]

        collected: List[Dict[str, Any]] = []
        collected.extend(self._parse_current_page())
        valid_count = sum(1 for r in collected if is_valid(r))
        logger.info(f"[page 1] 누적 수집: {len(collected)}개 (유효 {valid_count}개)")

        page = 1
        while valid_count < self.target_count and page < self.MAX_PAGES:
            page += 1
            if not self._click_page(page):
                logger.info(f"[page {page}] 버튼 없음 — 더 이상 페이지 없음, 수집 종료")
                break
            collected.extend(self._parse_current_page())
            valid_count = sum(1 for r in collected if is_valid(r))
            logger.info(f"[page {page}] 누적 수집: {len(collected)}개 (유효 {valid_count}개)")
        else:
            if page >= self.MAX_PAGES:
                logger.warning("최대 페이지 한도 도달 — 크롤링 종료")

        self.driver.quit()

        valid = [r for r in collected if is_valid(r)]
        self.results = valid[: self.target_count]

        if len(self.results) < self.target_count:
            logger.warning(
                f"목표({self.target_count}개) 미달성 — 최종 {len(self.results)}개만 확보됨"
            )
        else:
            logger.info(f"목표({self.target_count}개) 달성")

        return self.results

    def save_to_database(self) -> None:
        """수집된 리뷰를 csv로 저장한다. 저장 경로: {output_dir}/reviews_kyobo.csv"""
        os.makedirs(self.output_dir, exist_ok=True)
        save_path = os.path.join(self.output_dir, f"reviews_{self.SITE_NAME}.csv")

        df = pd.DataFrame(self.results, columns=["stars", "date", "review"])
        df.to_csv(save_path, index=False, encoding="utf-8-sig")

        logger.info(f"csv 저장 완료: {save_path} ({len(df)}행)")
