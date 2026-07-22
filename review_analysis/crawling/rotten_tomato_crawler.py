import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from review_analysis.crawling.base_crawler import BaseCrawler

class RottenTomatoCrawler(BaseCrawler):
    def __init__(self, output_dir: str):
        super().__init__(output_dir)
        self.base_url = f'https://www.rottentomatoes.com/m/interstellar_2014/reviews'
        self.driver = None

    def start_browser(self):
        options = Options()
        # options.add_argument('--headless=new')  # 화면 없이 실행. 눈으로 보고 싶으면 이 줄 삭제
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(options=options)
        self.driver.get(self.base_url)
        self._accept_cookies()

    def _accept_cookies(self):
        try:
            accept_btn = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            accept_btn.click()
        except TimeoutException:
            pass  # 배너가 안 뜬 경우 그냥 넘어감

    def scrape_reviews(self):
        self.start_browser()
        time.sleep(10)  # 확인용 임시 딜레이

    def save_to_database(self):
        pass
