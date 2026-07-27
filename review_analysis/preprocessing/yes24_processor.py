import os
import re

import pandas as pd
from kiwipiepy import Kiwi

from review_analysis.preprocessing.base_processor import BaseDataProcessor

# 의미 없는 일반 불용어 (형태소 분석 후 명사/용언 어근 기준으로 걸러냄)
STOPWORDS = {
    "것", "수", "등", "및", "때", "저", "제", "나", "너", "그", "이", "저희",
    "정도", "경우", "생각", "느낌", "점", "번", "책", "말", "듯",
    "하", "되", "있", "없", "같", "이러하", "그러하", "저러하",
}


class YES24Processor(BaseDataProcessor):
    def __init__(self, input_path: str, output_dir: str):
        super().__init__(input_path, output_dir)
        self.df: pd.DataFrame = pd.DataFrame()
        self.kiwi = Kiwi()

    # ------------------------------------------------------------------
    # 1. 전처리
    # ------------------------------------------------------------------
    def preprocess(self):
        df = pd.read_csv(self.input_path)

        # 팀 컨벤션에 맞춰 컬럼명 통일
        df = df.rename(columns={
            "date": "review_date",
            "rating": "review_stars",
            "review": "review_comment",
        })

        # 결측치 제거 (방어 코드 - 원본에는 결측치 없음)
        df = df.dropna(
            subset=["review_date", "review_stars", "review_comment"]
        ).copy()

        # 날짜 파싱, 파싱 실패(NaT) 행 제거
        df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce")
        df = df.dropna(subset=["review_date"])

        # 별점 범위(0~10) 벗어난 값 제거
        df["review_stars"] = pd.to_numeric(df["review_stars"], errors="coerce")
        df = df.dropna(subset=["review_stars"])
        df = df[(df["review_stars"] >= 0) & (df["review_stars"] <= 10)]

        # 별점 스케일 통일: YES24는 0~10 -> 팀 기준 0~5로 변환
        df["review_stars"] = df["review_stars"] / 2

        # 리뷰 텍스트 길이 기준 이상치 제거 (IQR)
        text_len = df["review_comment"].astype(str).str.len()
        q1, q3 = text_len.quantile(0.25), text_len.quantile(0.75)
        iqr = q3 - q1
        lower = max(10, q1 - 1.5 * iqr)  # 최소 10자 미만은 무조건 제거
        upper = q3 + 1.5 * iqr
        df = df[(text_len >= lower) & (text_len <= upper)]

        # 특수문자 제거 (한글, 영문, 숫자, 공백만 남김)
        df["review_comment_clean"] = (
            df["review_comment"]
            .astype(str)
            .apply(lambda x: re.sub(r"[^가-힣a-zA-Z0-9\s]", " ", x))
            .apply(lambda x: re.sub(r"\s+", " ", x).strip())
        )

        df = df.reset_index(drop=True)
        self.df = df
        return self.df

    # ------------------------------------------------------------------
    # 2. 파생변수 + 텍스트 벡터화
    # ------------------------------------------------------------------
    def feature_engineering(self):
        df = self.df

        # 파생변수 (5점 만점 기준 4점 이상 = 긍정)
        df["sentiment_label"] = (df["review_stars"] >= 4).astype(int)

        # 형태소 분석 -> 명사/용언 어근만 추출, 불용어 제거
        target_tags = {"NNG", "NNP", "VV", "VA"}

        def tokenize(text: str) -> str:
            tokens = self.kiwi.tokenize(text)
            words = [
                t.form for t in tokens
                if t.tag in target_tags and t.form not in STOPWORDS and len(t.form) > 1
            ]
            return " ".join(words)

        df["tokens"] = df["review_comment_clean"].apply(tokenize)

        # 토큰이 비어버린 행 제거 (전처리 후 분석 불가능한 리뷰)
        df = df[df["tokens"].str.len() > 0].reset_index(drop=True)

        # TF-IDF 벡터화
        from sklearn.feature_extraction.text import TfidfVectorizer

        vectorizer = TfidfVectorizer(max_features=300)
        tfidf_matrix = vectorizer.fit_transform(df["tokens"])
        tfidf_df = pd.DataFrame(
            tfidf_matrix.toarray(),
            columns=[f"tfidf_{w}" for w in vectorizer.get_feature_names_out()],
        )

        df = pd.concat(
            [df.reset_index(drop=True), tfidf_df.reset_index(drop=True)], axis=1
        )

        self.df = df
        return self.df

    # ------------------------------------------------------------------
    # 3. 저장
    # ------------------------------------------------------------------
    def save_to_database(self):
        os.makedirs(self.output_dir, exist_ok=True)
        out_path = os.path.join(self.output_dir, "preprocessed_reviews_yes24.csv")
        self.df.to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"저장 완료: {out_path} ({len(self.df)}행)")
        return out_path