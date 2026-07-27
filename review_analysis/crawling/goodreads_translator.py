import time

import pandas as pd
from deep_translator import GoogleTranslator

df = pd.read_csv("database/reviews_goodreads.csv")

translator = GoogleTranslator(source="auto", target="ko")


def translate_with_retry(text: str, retries: int = 3, delay: float = 2.0) -> str:
    """구글 번역 무료 엔드포인트는 대량 호출시 에러가 잦기에 텀을 두고 재시도한다.

    끝까지 실패하면 원문을 그대로 반환해 전체 작업이 중단되지 않게 한다.
    """
    if not text:
        return ""
    for attempt in range(retries):
        try:
            result = translator.translate(text)
            time.sleep(0.3)  # 요청 사이 딜레이로 연속 호출로 인한 차단 위험을 줄임
            return result
        except Exception:
            if attempt == retries - 1:
                print("번역 실패, 원문 유지:", text[:50])
                return text
            time.sleep(delay)


df["review"] = df["review"].fillna("").apply(translate_with_retry)

df.to_csv(
    "database/reviews_goodreads_ko.csv",
    index=False,
    encoding="utf-8-sig"
)

print("Translation completed.")

