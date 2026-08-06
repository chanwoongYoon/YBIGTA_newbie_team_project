from abc import ABC, abstractmethod

import pandas as pd
from pymongo.collection import Collection

class BaseDataProcessor:
    def __init__(self, input_collection: Collection, output_collection: Collection):
        self.input_collection = input_collection
        self.output_collection = output_collection
        self.df = pd.DataFrame(list(input_collection.find()))
        if "_id" in self.df.columns:
            self.df = self.df.drop(columns=["_id"])

    @abstractmethod
    def preprocess(self):
        pass

    @abstractmethod
    def feature_engineering(self):
        pass

    def save_to_database(self):
        '''전처리 완료된 데이터프레임을 MongoDB의 output_collection에 저장하는 함수입니다.
        재실행 시 결과가 누적되지 않도록 기존 데이터는 지우고 새로 저장합니다.'''
        self.output_collection.delete_many({})
        records = self.df.to_dict("records")
        if records:
            self.output_collection.insert_many(records)
        return self.output_collection.name
