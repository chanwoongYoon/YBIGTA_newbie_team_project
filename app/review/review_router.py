from fastapi import APIRouter, HTTPException, status

from database.mongodb_connection import mongo_db
from app.responses.base_response import BaseResponse
from review_analysis.preprocessing.goodreads_processor import GoodreadsProcessor
from review_analysis.preprocessing.kyobo_processor import KyoboProcessor
from review_analysis.preprocessing.yes24_processor import YES24Processor

review = APIRouter(prefix="/review")

PROCESSOR_MAP = {
    "goodreads": GoodreadsProcessor,
    "kyobo": KyoboProcessor,
    "yes24": YES24Processor,
}


@review.post("/preprocess/{site_name}", response_model=BaseResponse[dict], status_code=status.HTTP_200_OK)
def preprocess_reviews(site_name: str) -> BaseResponse[dict]:
    processor_cls = PROCESSOR_MAP.get(site_name)
    if processor_cls is None:
        raise HTTPException(status_code=404, detail=f"Unsupported site_name: {site_name}")

    input_collection = mongo_db[f"reviews_{site_name}"]
    output_collection = mongo_db[f"preprocessed_reviews_{site_name}"]

    if input_collection.count_documents({}) == 0:
        raise HTTPException(status_code=404, detail=f"No raw data found in reviews_{site_name}")

    processor = processor_cls(input_collection, output_collection)
    processor.preprocess()
    processor.feature_engineering()
    processor.save_to_database()

    return BaseResponse(
        status="success",
        data={"site": site_name, "processed_count": len(processor.df)},
        message=f"{site_name} 리뷰 전처리 완료.",
    )
