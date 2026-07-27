
"""Goodreads Crawler입니다. 
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from review_analysis.crawling.base_crawler import BaseCrawler


logger = logging.getLogger(__name__)

DEFAULT_BOOK_URL = (
    "https://www.goodreads.com/book/show/58481813/reviews?"
    "reviewFilters=eyJhZnRlciI6Ik1UUXdNU3d4TnpNM01ESTFNVGd5TlRZNSJ9"
)


GOODREADS_SELECTORS = {
    "review_card": "article.ReviewCard",
    "review_text": "[data-testid='contentContainer'] .Formatted",
    "rating": "[aria-label*='Rating']",
    "date": "a[href*='/review/show/']",
    "next_page": "a[aria-label='Next page']",
    "expand_review": "button[aria-label*='more'], button[aria-label*='More']",
}


class GoodreadsCrawler(BaseCrawler):

    SITE_NAME = "goodreads"

    def __init__(
        self,
        output_dir: str,
        book_url: str = DEFAULT_BOOK_URL,
        target_count: int = 100,
        wait_seconds: int = 10,
    ) -> None:
        super().__init__(output_dir)
        self.base_url = book_url
        self.target_count = target_count
        self.wait_seconds = wait_seconds
        self.driver: Optional[webdriver.Chrome] = None
        self.results: List[Dict[str, Any]] = []

    def start_browser(self) -> None:
        """크롬 창을 열고, 불편한 편의점 페이지로 이동한다."""
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--lang=en-US")

        self.driver = webdriver.Chrome(options=options)
        self.driver.get(self.base_url)
        logger.info("Opened Goodreads book page: %s", self.base_url)

    def _wait_for_review_cards(self) -> bool:
        """리뷰 카드가 로딩될 때까지 기다린다. 로딩 실패시 false를 반환한다."""
        assert self.driver is not None
        try:
            WebDriverWait(self.driver, self.wait_seconds).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, GOODREADS_SELECTORS["review_card"])
                )
            )
            return True
        except TimeoutException:
            return False

    def _expand_visible_reviews(self) -> None:
        """더보기를 눌러서 리뷰를 펼친다. 펼칠 수 없는 리뷰는 무시한다."""
        assert self.driver is not None
        for button in self.driver.find_elements(By.CSS_SELECTOR, GOODREADS_SELECTORS["expand_review"]):
            try:
                self.driver.execute_script("arguments[0].click();", button)
            except Exception:  # A re-rendered/hidden button can safely be skipped.
                continue

    @staticmethod
    def _parse_stars(card: Tag) -> Optional[float]:
        """웹페이지 카드에서 Goodreads 리뷰 별점을 추출해서, ``GOODREADS_SELECTORS['rating']``를 업데이트한다.
        """
        rating_el = card.select_one(GOODREADS_SELECTORS["rating"])
        if rating_el is None:
            return None

        label = rating_el.get("aria-label", "")
        if not isinstance(label, str):
            label = ""
        match = re.search(r"([0-5](?:\.\d+)?)\s*(?:out of|/)?\s*5", label, re.I)
        if not match:
            match = re.search(r"rating\s*([0-5](?:\.\d+)?)", label, re.I)
        return float(match.group(1)) if match else None

    @staticmethod
    def _parse_date(card: Tag) -> Optional[str]:
        """웹페이지 카드에서 Goodreads 리뷰 날짜를 ISO ``YYYY-MM-DD`` 형식으로 추출한다. ``date``는 현재 리뷰 퍼머링크를 가리킨다.
        퍼머링크에 날짜 텍스트가 포함되어 있지 않은 경우, 표시된 리뷰 날짜를 포함하는 요소로 변경한다.
        """
        date_el = card.select_one(GOODREADS_SELECTORS["date"])
        if date_el is None:
            return None

        raw = date_el.get_text(" ", strip=True)
        raw = re.sub(r"^(?:updated|reviewed|read)\s+", "", raw, flags=re.I)
        for date_format in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw, date_format).date().isoformat()
            except ValueError:
                continue
        return raw or None

    @staticmethod
    def _parse_review_text(card: Tag) -> str:
        """웹페이지 카드에서 공백을 제외하고 리뷰 바디만 추출한다."""
        text_el = card.select_one(GOODREADS_SELECTORS["review_text"])
        if text_el is None:
            return ""
        for control in text_el.select("button, svg"):
            control.decompose()
        return text_el.get_text(" ", strip=True)

    def _parse_current_page(self) -> List[Dict[str, Any]]:
        assert self.driver is not None
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        reviews: List[Dict[str, Any]] = []
        for card in soup.select(GOODREADS_SELECTORS["review_card"]):
            reviews.append(
                {
                    "stars": self._parse_stars(card),
                    "date": self._parse_date(card),
                    "review": self._parse_review_text(card),
                }
            )
        return reviews

    def _go_to_next_page(self) -> bool:
        """Follow Goodreads' next-page control, returning False on the last page."""
        assert self.driver is not None
        next_buttons = self.driver.find_elements(By.CSS_SELECTOR, GOODREADS_SELECTORS["next_page"])
        if not next_buttons:
            return False

        next_button = next_buttons[0]
        if next_button.get_attribute("aria-disabled") == "true":
            return False
        previous_url = self.driver.current_url
        self.driver.execute_script("arguments[0].click();", next_button)
        try:
            WebDriverWait(self.driver, self.wait_seconds).until(
                lambda driver: driver.current_url != previous_url
            )
            return self._wait_for_review_cards()
        except TimeoutException:
            return False

    def _save_debug_files(self) -> None:
        """Save the failed page to help update the Goodreads-specific selectors."""
        assert self.driver is not None
        os.makedirs(self.output_dir, exist_ok=True)
        html_path = os.path.join(self.output_dir, "goodreads_debug_page.html")
        png_path = os.path.join(self.output_dir, "goodreads_debug_screenshot.png")
        with open(html_path, "w", encoding="utf-8") as file:
            file.write(self.driver.page_source)
        self.driver.save_screenshot(png_path)
        logger.error(
            "Could not find review cards. Inspect %s and %s, then update GOODREADS_SELECTORS.",
            html_path,
            png_path,
        )

    def scrape_reviews(self) -> List[Dict[str, Any]]:
        """Collect up to ``target_count`` valid reviews across the review pages."""
        self.start_browser()
        assert self.driver is not None
        collected: List[Dict[str, Any]] = []
        seen = set()

        try:
            if not self._wait_for_review_cards():
                self._save_debug_files()
                return []

            while len(collected) < self.target_count:
                self._expand_visible_reviews()
                for review in self._parse_current_page():
                    key = (review["stars"], review["date"], review["review"])
                    if key in seen or review["stars"] is None or not review["date"]:
                        continue
                    seen.add(key)
                    collected.append(review)
                    if len(collected) >= self.target_count:
                        break

                logger.info("Collected %d Goodreads reviews.", len(collected))
                if len(collected) >= self.target_count or not self._go_to_next_page():
                    break
        finally:
            self.driver.quit()
            self.driver = None

        self.results = collected
        return self.results

    def save_to_database(self) -> None:
        """Write the most recently collected reviews to ``reviews_goodreads.csv``."""
        os.makedirs(self.output_dir, exist_ok=True)
        save_path = os.path.join(self.output_dir, f"reviews_{self.SITE_NAME}.csv")
        pd.DataFrame(self.results, columns=["stars", "date", "review"]).to_csv(
            save_path, index=False, encoding="utf-8-sig"
        )
        logger.info("Saved %d Goodreads reviews to %s", len(self.results), save_path)
