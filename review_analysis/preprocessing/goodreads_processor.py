import os
import re 
from datetime import datetime
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer

from review_analysis.preprocessing.base_processor import BaseDataProcessor

class GoodreadsProcessor(BaseDataProcessor):
    def __init__(self, input_collection, output_collection):
        self.input_collection = input_collection
        self.output_collection = output_collection
        self.df = pd.DataFrame(list(input_collection.find()))
        if "_id" in self.df.columns:
            self.df = self.df.drop(columns=["_id"])

    def preprocess(self):
        '''결측치 확인, 이상치 처리, 텍스트 정리를 하는 전처리 함수입니다.'''
        #1. 결측치 확인
        if self.df.isnull().values.any():
            self.df = self.df.dropna()

        #2. 이상치 처리 (별점 범위)
        self.df = self.df[(self.df['stars'] >= 1) & (self.df['stars'] <= 5)]

        #3. 텍스트 정리
        ## 특수문자 제거
        import re

        self.df["review"] = self.df["review"].apply(
            lambda x: re.sub(r"[^가-힣a-zA-Z0-9\s]", " ", str(x))
        )
        ## 공백 제거
        self.df["review"] = self.df["review"].str.replace(
            r"\s+", " ", regex=True
        ).str.strip()

        #2-1. 이상치 처리 (정제된 텍스트 기준 리뷰 길이)
        review_len = self.df['review'].str.len()
        self.df = self.df[(review_len >= 10) & (review_len <= 1000)]

    def feature_engineering(self):
        '''별점 4점이상 긍정신호로 해석하는 파생변수 생성, 텍스트 벡터화하는 
        Feature Engineering함수입니다.'''

        df = self.df

        # 파생변수: 감성 레이블 (5점 만점 기준 4점 이상 = 긍정)
        df["is_positive"] = (df["stars"] >= 4).astype(int)


        # TF-IDF 벡터화

        vectorizer = TfidfVectorizer(max_features=300)

        #전처리한 리뷰를 TF-IDF 벡터화하고, feature_names를 변수에 저장
        self.tfidf_matrix = vectorizer.fit_transform(self.df["review"])
        self.feature_names = vectorizer.get_feature_names_out()

        #tf-idf 결과 행렬을 데이터프레임으로 변환하고 기존 데이터프레임과 합치기
        tfidf_df = pd.DataFrame(
        self.tfidf_matrix.toarray(),
        columns=self.feature_names
        )

        self.df = pd.concat(
            [self.df.reset_index(drop=True),
            tfidf_df.reset_index(drop=True)],
            axis=1
        )

    def save_to_database(self):
        '''전처리 완료된 데이터프레임을 MongoDB의 output_collection에 저장하는 함수입니다.
        재실행 시 결과가 누적되지 않도록 기존 데이터는 지우고 새로 저장합니다.'''
        self.output_collection.delete_many({})
        records = self.df.to_dict("records")
        if records:
            self.output_collection.insert_many(records)
        return self.output_collection.name


