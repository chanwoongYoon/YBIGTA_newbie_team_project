from review_analysis.preprocessing.base_processor import BaseDataProcessor
from pathlib import Path
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from kiwipiepy import Kiwi
import os

column_name = {
    "review_date" : "date",
    "review_stars" : "stars",
    "review_comment" : "review"
}

class KyoboProcessor(BaseDataProcessor):
    def __init__(self, input_path: str, output_path: str):
        super().__init__(input_path, output_path)
        self.kiwi = Kiwi()

    def load(self):
        try:
            df = pd.read_csv(self.input_path, encoding='utf-8-sig')
        except UnicodeDecodeError:
            df = pd.read_csv(self.input_path, encoding='cp949')
        print(f"[{Path(self.input_path).stem}] shape={df.shape}")
        print("컬럼:", df.columns.tolist())
        return df


    def preprocess(self):
        df = self.load()

        # 별점 스케일링
        df[column_name["review_stars"]] = df[column_name["review_stars"]] * (5/4)

        # 결측치 처리 로직
        if(df.isna().sum().sum() == 0):
            print("결측치 없음")
        else:
            print("결측치 있음. 전처리 필요")
            df = df.dropna(subset=[column_name["review_date"],column_name["review_stars"],column_name["review_comment"]])

        # 이상치 처리
        print(df[column_name["review_stars"]].describe())
        has_outlier = df[column_name["review_stars"]].max() > 5 or df[column_name["review_stars"]].min() < 1
        if has_outlier:
            print("이상치 있음 -> clip 처리")
            df[column_name["review_stars"]] = df[column_name["review_stars"]].clip(lower=1, upper=5)
        else:
            print("이상치 없음")

        # 텍스트 데이터 전처리
        df[column_name["review_comment"]] = (
            df[column_name["review_comment"]]
            .str.replace("\n", " ", regex=False)   # 줄바꿈 -> 공백
            .str.replace(r"[~!?.,]{2,}", " ", regex=True)  # 물결/느낌표 등 2번 이상 반복되는 특수문자 -> 공백
            .str.replace(r"\s+", " ", regex=True)  # 연속 공백 -> 공백 1개
            .str.strip()  # 양쪽 끝 공백 제거
        )

        # 파생변수
        self.df = df
        return df

    # review컬럼을 형태소 분석된 텍스트로 바꾸기
    def tokenize_review(self, text: str) -> str:
        tokens = self.kiwi.tokenize(text)
        keep_tags = {"NNG", "NNP", "VV", "VA"}
        words = [t.form for t in tokens if t.tag in keep_tags]
        return " ".join(words)
    
    def feature_engineering(self):
        df = self.df

        # sentiment_label: 별점 기준으로 긍정/부정 나누기
        df["sentiment_label"] = (df[column_name["review_stars"]] >= 4).astype(int)

        # review 컬럼을 형태소 분석된 텍스트로 바꾸기
        df[column_name["review_comment"]] = df[column_name["review_comment"]].apply(self.tokenize_review)

        #텍스트 벡터화
        vectorizer = TfidfVectorizer(max_features=1000)
        tfidf_matrix = vectorizer.fit_transform(df[column_name["review_comment"]])

        self.vectorizer = vectorizer
        self.tfidf_matrix = tfidf_matrix

        self.df = df
        return df

    def save_to_database(self):
        os.makedirs(self.output_dir, exist_ok=True)
        save_path = os.path.join(self.output_dir, "preprocessed_reviews_kyobo.csv")
        self.df.to_csv(save_path, index=False, encoding="utf-8-sig")
        print(f"저장 완료: {save_path} (shape={self.df.shape})")

    def view_preprocessing(self):
        print(self.df["sentiment_label"].describe())
        print(self.df.shape)
        print(self.df.columns)
        print(self.df.isna().sum())
        print(self.df.sample(20))
        print(f'텍스트 벡터화 잘 되었나 확인 : {self.tfidf_matrix.shape}')
        print(f'실제로 어떤 단어들이 들어갔나 확인 : {self.vectorizer.get_feature_names_out()}')