"""A small, ordinary Selenium crawler for a Goodreads book's reviews.

Before running this crawler, inspect the review page in a browser and update the
CSS selectors in ``GOODREADS_SELECTORS`` if Goodreads has changed its markup.
Those selectors are intentionally kept in one place because they are specific
to Goodreads' HTML, not to the crawler logic.
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


# TODO(Goodreads HTML): Verify these against the current Goodreads review page.
# The first selector is the repeating *one review* container.  The remaining
# selectors are searched inside each review container.
GOODREADS_SELECTORS = {
    "review_card": "article.ReviewCard",
    "review_text": "[data-testid='contentContainer'] .Formatted",
    "rating": "[aria-label*='Rating']",
    "date": "a[href*='/review/show/']",
    "next_page": "a[aria-label='Next page']",
    "expand_review": "button[aria-label*='more'], button[aria-label*='More']",
}


class GoodreadsCrawler(BaseCrawler):
    """Collect star rating, review date, and text from one Goodreads book page.

    ``book_url`` must be a Goodreads book URL, for example
    ``https://www.goodreads.com/book/show/<book-id>``.  This class does not use
    a proxy or an automation-detection bypass; it opens Chrome through Selenium
    and follows Goodreads' ordinary review pagination.
    """

    SITE_NAME = "goodreads"

    def __init__(
        self,
        output_dir: str,
        book_url: str,
        target_count: int = 100,
        wait_seconds: int = 10,
    ) -> None:
        super().__init__(output_dir)
        if not book_url:
            raise ValueError("book_url is required. Pass a Goodreads book URL.")

        self.base_url = book_url
        self.target_count = target_count
        self.wait_seconds = wait_seconds
        self.driver: Optional[webdriver.Chrome] = None
        self.results: List[Dict[str, Any]] = []

    def start_browser(self) -> None:
        """Open Chrome normally and navigate to the supplied Goodreads book."""
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--lang=en-US")

        self.driver = webdriver.Chrome(options=options)
        self.driver.get(self.base_url)
        logger.info("Opened Goodreads book page: %s", self.base_url)

    def _wait_for_review_cards(self) -> bool:
        """Wait until at least one Goodreads review card is present."""
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
        """Click visible ``more`` controls so their text is included in page source."""
        assert self.driver is not None
        for button in self.driver.find_elements(By.CSS_SELECTOR, GOODREADS_SELECTORS["expand_review"]):
            try:
                self.driver.execute_script("arguments[0].click();", button)
            except Exception:  # A re-rendered/hidden button can safely be skipped.
                continue

    @staticmethod
    def _parse_stars(card: Tag) -> Optional[float]:
        """Extract ``4`` from an accessible label such as ``Rating 4 out of 5``.

        TODO(Goodreads HTML): update ``GOODREADS_SELECTORS['rating']`` if the
        rating element no longer exposes an ``aria-label``.
        """
        rating_el = card.select_one(GOODREADS_SELECTORS["rating"])
        if rating_el is None:
            return None

        label = rating_el.get("aria-label", "")
        match = re.search(r"([0-5](?:\.\d+)?)\s*(?:out of|/)?\s*5", label, re.I)
        if not match:
            match = re.search(r"rating\s*([0-5](?:\.\d+)?)", label, re.I)
        return float(match.group(1)) if match else None

    @staticmethod
    def _parse_date(card: Tag) -> Optional[str]:
        """Return a Goodreads review date in ISO ``YYYY-MM-DD`` form when possible.

        TODO(Goodreads HTML): ``date`` currently points at the review permalink.
        Change it to the element that contains the displayed review date if the
        permalink does not include date text on the page you are collecting.
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
        """Extract only the review body, excluding buttons and whitespace."""
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
