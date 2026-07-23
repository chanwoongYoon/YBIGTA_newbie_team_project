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


class KakaoCrawler(BaseCrawler):
    """카카오맵 장소 리뷰(별점·날짜·본문) 크롤러.

    경복궁(place_id=18619553) 페이지에서 리뷰를 수집한다.
    Selenium으로 동적 로딩(더보기 버튼/무한스크롤, 본문 더보기 펼치기)을 처리하고,
    최종적으로 BeautifulSoup으로 page_source를 파싱해 별점/날짜/본문을 추출한다.

    본문이 있는 리뷰를 우선적으로 채우되, target_count를 못 채울 만큼 부족하면
    본문 없는(별점+날짜만 있는) 리뷰로 나머지 슬롯을 채워 총 target_count개를 유지한다.
    """

    SITE_NAME = "kakao"
    MAX_ITERS = 500  # 무한루프 방지 안전장치

    def __init__(self, output_dir: str, target_count: int = 500):
        """
        Args:
            output_dir: 크롤링 결과 csv를 저장할 디렉토리 경로 (예: "database")
            target_count: 최종적으로 유지할 리뷰 개수 (본문 있는 것 우선, 부족하면 본문 없는 것으로 채움)
        """
        super().__init__(output_dir)
        self.base_url = "https://place.map.kakao.com/18619553#review"
        self.target_count = target_count
        self.driver: Optional[webdriver.Chrome] = None
        self.results: List[Dict[str, Any]] = []

    def start_browser(self) -> None:
        """Chrome 드라이버를 실행하고 대상 페이지로 이동한다."""
        self.driver = webdriver.Chrome()
        self.driver.get(self.base_url)
        logger.info(f"브라우저 시작 및 페이지 이동: {self.base_url}")

    def _load_one_batch(self) -> bool:
        """리뷰 목록을 한 번(더보기 버튼 클릭 또는 스크롤) 추가 로딩한다.

        Returns:
            추가로 로딩된 콘텐츠가 있으면 True, 더 로딩할 게 없으면 False.
        """
        assert self.driver is not None
        more_btns = self.driver.find_elements(By.CLASS_NAME, "link_more")
        if more_btns:
            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", more_btns[0]
                )
                time.sleep(0.3)
                self.driver.execute_script("arguments[0].click();", more_btns[0])
                time.sleep(random.uniform(1.0, 1.8))
                return True
            except (ElementClickInterceptedException, StaleElementReferenceException):
                time.sleep(1)
                return True

        before_height = self.driver.execute_script("return document.body.scrollHeight")
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)
        after_height = self.driver.execute_script("return document.body.scrollHeight")
        return after_height != before_height

    def _expand_all_truncated_reviews(self) -> None:
        """현재 로딩된 리뷰 중 '더보기' 상태인 본문을 전부 펼친다."""
        assert self.driver is not None
        btn_mores = self.driver.find_elements(By.CSS_SELECTOR, ".desc_review .btn_more")
        for btn in btn_mores:
            text = (btn.get_attribute("textContent") or "").strip()
            if text == "더보기":
                try:
                    self.driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.05)
                except (StaleElementReferenceException, ElementClickInterceptedException):
                    continue

    @staticmethod
    def _parse_stars(block: Any) -> Optional[float]:
        """review_detail 블록(BeautifulSoup Tag)에서 별점을 추출한다."""
        for el in block.find_all("span", class_="screen_out"):
            text = el.get_text(strip=True)
            try:
                return float(text)
            except ValueError:
                continue
        return None

    @staticmethod
    def _parse_date(block: Any) -> Optional[str]:
        """review_detail 블록에서 작성 날짜를 'YYYY-MM-DD' 형식으로 추출한다."""
        date_el = block.find("span", class_="txt_date")
        if date_el is None:
            return None
        raw = date_el.get_text(strip=True).rstrip(".")
        parts = raw.split(".")
        if len(parts) == 3 and all(p.strip().isdigit() for p in parts):
            y, m, d = (p.strip() for p in parts)
            return f"{y}-{int(m):02d}-{int(d):02d}"
        return raw or None

    @staticmethod
    def _parse_review_text(block: Any) -> str:
        """review_detail 블록에서 '더보기/접기' 버튼 텍스트를 제외한 순수 본문만 추출한다."""
        desc_el = block.find("p", class_="desc_review")
        if desc_el is None:
            return ""
        btn = desc_el.find("span", class_="btn_more")
        if btn is not None:
            btn.decompose()
        return desc_el.get_text(strip=True)

    def _parse_all_reviews(self) -> List[Dict[str, Any]]:
        """현재 page_source를 BeautifulSoup으로 파싱해 전체 리뷰(별점/날짜/본문)를 추출한다."""
        assert self.driver is not None
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        blocks = soup.find_all("div", class_="review_detail")

        parsed: List[Dict[str, Any]] = []
        for block in blocks:
            parsed.append({
                "stars": self._parse_stars(block),
                "date": self._parse_date(block),
                "review": self._parse_review_text(block),
            })
        return parsed

    @staticmethod
    def _select_final(parsed: List[Dict[str, Any]], target_count: int) -> List[Dict[str, Any]]:
        """별점+날짜가 있는 리뷰 중 본문 있는 것을 우선 채우고,
        부족하면 본문 없는(별점만 있는) 리뷰로 나머지를 채워 최대 target_count개를 고른다.
        별점 또는 날짜 자체가 없는 리뷰는 애초에 제외한다.
        """
        base_valid = [r for r in parsed if r["stars"] is not None and r["date"]]
        with_text = [r for r in base_valid if r["review"]]
        without_text = [r for r in base_valid if not r["review"]]

        selected = with_text[:target_count]
        if len(selected) < target_count:
            need = target_count - len(selected)
            selected += without_text[:need]
        return selected

    def scrape_reviews(self) -> List[Dict[str, Any]]:
        """본문 있는 유효 리뷰(별점+날짜+본문)가 target_count개 모이거나,
        더 이상 로딩할 리뷰가 없을 때까지 크롤링한다.

        본문 있는 리뷰가 부족한 상태로 로딩이 끝나면, 별점+날짜만 있는 리뷰로
        나머지 슬롯을 채워 최종적으로 최대 target_count개를 유지한다.

        Returns:
            {"stars": float | None, "date": str | None, "review": str} 딕셔너리 리스트
        """
        self.start_browser()
        assert self.driver is not None

        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "review_detail"))
            )
        except TimeoutException:
            logger.error("리뷰 요소를 찾지 못함 (review_detail 미검출)")
            self.driver.quit()
            return []

        parsed: List[Dict[str, Any]] = []
        for i in range(self.MAX_ITERS):
            self._expand_all_truncated_reviews()
            parsed = self._parse_all_reviews()

            with_text_count = sum(
                1 for r in parsed if r["stars"] is not None and r["date"] and r["review"]
            )
            valid_any_count = sum(1 for r in parsed if r["stars"] is not None and r["date"])
            logger.info(
                f"[{i}회차] 로딩된 리뷰: {len(parsed)}개 / "
                f"본문 있는 유효 리뷰: {with_text_count}개 / "
                f"별점+날짜만 있는 리뷰 포함 전체 유효: {valid_any_count}개"
            )

            if with_text_count >= self.target_count:
                logger.info(f"본문 있는 유효 리뷰 {with_text_count}개로 목표 달성")
                break

            has_more = self._load_one_batch()
            if not has_more:
                logger.info("더 이상 로딩할 리뷰 없음 — 현재까지 데이터로 마무리")
                break
        else:
            logger.warning("반복 횟수 한도 도달 — 크롤링 종료")

        self.driver.quit()
        self.results = self._select_final(parsed, self.target_count)
        self._validate_results(self.results, parsed)
        return self.results

    def _validate_results(
        self, selected: List[Dict[str, Any]], all_parsed: List[Dict[str, Any]]
    ) -> None:
        """최종 선정 결과와 전체 로딩분을 비교해 검증 로그를 출력한다."""
        total_loaded = len(all_parsed)
        total_selected = len(selected)
        with_text = sum(1 for r in selected if r["review"])
        without_text = total_selected - with_text

        logger.info("=== 수집 결과 검증 ===")
        logger.info(f"전체 로딩(필터링 전): {total_loaded}개")
        logger.info(
            f"최종 선정: {total_selected}개 "
            f"(본문 있음 {with_text}개 / 본문 없음-별점만 {without_text}개)"
        )

        if total_selected < self.target_count:
            logger.warning(
                f"목표({self.target_count}개) 미달성 — 최종 {total_selected}개만 확보됨 "
                f"(별점+날짜가 있는 리뷰 자체가 부족)"
            )
        elif without_text > 0:
            logger.warning(
                f"목표({self.target_count}개)는 채웠지만 그중 {without_text}개는 본문 없이 "
                f"별점만으로 채워짐 — 과제 최소조건(리뷰 내용 필수)상 제출 전 재확인 필요"
            )
        else:
            logger.info(f"목표({self.target_count}개) 전부 본문 포함으로 달성")

    def save_to_database(self) -> None:
        """최종 선정된 리뷰(본문 있음 우선 + 부족분 본문 없음으로 채움)를 csv로 저장한다.

        저장 경로: {output_dir}/reviews_kakao.csv
        """
        os.makedirs(self.output_dir, exist_ok=True)
        save_path = os.path.join(self.output_dir, f"reviews_{self.SITE_NAME}.csv")

        df = pd.DataFrame(self.results, columns=["stars", "date", "review"])
        df.to_csv(save_path, index=False, encoding="utf-8-sig")

        logger.info(f"csv 저장 완료: {save_path} ({len(df)}행)")