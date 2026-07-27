import csv
from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup

# 프로젝트 속 database 폴더에 최종 csv file을 저장한다.
DATABASE_DIR = Path(__file__).resolve().parent.parent.parent / "database"

GRAPHQL_URL = "https://kxbwmqov6jgg3daaamb744ycu4.appsync-api.us-east-1.amazonaws.com/graphql"

HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://www.goodreads.com",
    "Referer": "https://www.goodreads.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
    "X-Api-Key": "da2-xpgsdydkbregjhpr6ejzqdhuwy",
}

QUERY = """
query getReviews($filters: BookReviewsFilterInput!, $pagination: PaginationInput) {
  getReviews(filters: $filters, pagination: $pagination) {
    totalCount
    edges {
      node {
        id
        text
        rating
        createdAt
        updatedAt
        likeCount
        commentCount
        creator {
          name
          id
        }
      }
    }
    pageInfo {
      prevPageToken
      nextPageToken
    }
  }
}
"""

MAX_REVIEWS = 500

DEFAULT_PAYLOAD: Dict[str, Any] = {
    "operationName": "getReviews",
    "variables": {
        "filters": {
            "resourceType": "WORK",
            "resourceId": "kca://work/amzn1.gr.work.v3.WZ5U__DBtwXHUGx5"
        },
        "pagination": {
            "after": None,
            "limit": 30
        }
    },
    "query": QUERY
}


def fetch_reviews(max_reviews: int = MAX_REVIEWS, delay_seconds: float = 1.0) -> List[Dict[str, Any]]:
    '''
    Goodreads API 호출을 통해 리뷰를 수집하는 함수. 페이지네이션에 사용되는 nextPageToken을
    활용하여 최대 max_reviews 개수만큼 리뷰를 수집한다.
    '''
    reviews: List[Dict[str, Any]] = []
    payload: Dict[str, Any] = {
        "operationName": DEFAULT_PAYLOAD["operationName"],
        "variables": {
            "filters": DEFAULT_PAYLOAD["variables"]["filters"].copy(),
            "pagination": DEFAULT_PAYLOAD["variables"]["pagination"].copy(),
        },
        "query": DEFAULT_PAYLOAD["query"],
    }

    while True:
        response = requests.post(
            GRAPHQL_URL,
            headers=HEADERS,
            json=payload,
        )
        response.raise_for_status()

        result = response.json()
        data = result["data"]["getReviews"]

        for edge in data["edges"]:
            if len(reviews) >= max_reviews:
                break

            node = edge["node"]
            if not node["rating"] or not node["createdAt"]:
                continue

            created_date = datetime.fromtimestamp(
                node["createdAt"] / 1000, tz=timezone.utc
            ).date().isoformat()
            review_text = BeautifulSoup(node["text"] or "", "html.parser").get_text(" ", strip=True)

            reviews.append({
                "stars": node["rating"],
                "date": created_date,
                "review": review_text,
            })

        print(f"Collected {len(reviews)} reviews")

        if len(reviews) >= max_reviews:
            print(f"Reached cap of {max_reviews} reviews.")
            break

        next_token = data["pageInfo"]["nextPageToken"]
        if not next_token:
            break

        payload["variables"]["pagination"]["after"] = next_token
        time.sleep(delay_seconds)

    return reviews


def save_reviews_csv(reviews: List[Dict[str, Any]], save_path: Path = DATABASE_DIR / "reviews_goodreads.csv") -> None:
    '''수집한 리뷰를 csv파일로 저장한다.'''
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    with open(save_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["stars", "date", "review"])
        writer.writeheader()
        writer.writerows(reviews)

    print(f"Done! {len(reviews)} reviews saved to {save_path}")


def main():
    reviews = fetch_reviews()
    if not reviews:
        raise RuntimeError("No reviews collected; cannot write reviews_goodreads.csv")
    save_reviews_csv(reviews)


if __name__ == "__main__":
    main()