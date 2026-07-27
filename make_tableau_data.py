"""태블로용 데이터 생성 스크립트

database/ 안의 preprocessed_reviews_*.csv 를 모두 찾아
태블로가 바로 쓸 수 있는 long format 파일 2개를 만든다.

- tableau/tableau_reviews.csv   : 리뷰 단위 (EDA + 시계열 비교용)
- tableau/tableau_keywords.csv  : 사이트별 키워드 빈도 (텍스트 비교용)

리뷰 길이는 파생변수가 아니라 전처리된 리뷰 본문에서 직접 계산한다.

레포 루트에서 실행: python3 make_tableau_data.py
"""
import glob
import os
import re
from collections import Counter

import pandas as pd

DB_DIR = "database"
OUT_DIR = "tableau"
os.makedirs(OUT_DIR, exist_ok=True)

files = sorted(glob.glob(os.path.join(DB_DIR, "preprocessed_reviews_*.csv")))
if not files:
    raise SystemExit("preprocessed_reviews_*.csv 파일이 없습니다.")

print(f"발견한 파일 {len(files)}개:")
for f in files:
    print("  -", os.path.basename(f))

review_frames = []
keyword_frames = []

for path in files:
    site = re.sub(r"^preprocessed_reviews_", "",
                  os.path.splitext(os.path.basename(path))[0])
    df = pd.read_csv(path)

    # ---------------- 리뷰 단위 테이블 ----------------
    out = pd.DataFrame()
    out["site"] = [site] * len(df)
    out["review_id"] = range(1, len(df) + 1)

    # 날짜
    if "review_date" in df.columns:
        out["review_date"] = pd.to_datetime(df["review_date"], errors="coerce")
        out["year"] = out["review_date"].dt.year
        out["month"] = out["review_date"].dt.to_period("M").astype(str)

    # 별점 (팀 기준 0~5 스케일)
    if "review_stars" in df.columns:
        out["review_stars"] = pd.to_numeric(df["review_stars"], errors="coerce")

    # 리뷰 길이 — 전처리된 본문에서 직접 계산 (파생변수 사용 안 함)
    for col in ["review_comment_clean", "review_comment"]:
        if col in df.columns:
            out["review_length"] = df[col].astype(str).str.len()
            break

    # 감성 레이블 (팀 공통 파생변수) — 없으면 별점으로 계산
    if "sentiment_label" in df.columns:
        out["sentiment_label"] = pd.to_numeric(df["sentiment_label"], errors="coerce")
    elif "review_stars" in out.columns:
        out["sentiment_label"] = (out["review_stars"] >= 4).astype(int)

    if "sentiment_label" in out.columns:
        out["sentiment_kor"] = out["sentiment_label"].map({1: "긍정", 0: "부정"})

    review_frames.append(out)

    # ---------------- 키워드 빈도 테이블 ----------------
    if "tokens" in df.columns:
        counter: Counter = Counter()
        for tok in df["tokens"].dropna().astype(str):
            counter.update(tok.split())

        total = sum(counter.values())
        kdf = pd.DataFrame(counter.most_common(50), columns=["word", "count"])
        kdf["site"] = site
        kdf["ratio"] = kdf["count"] / total          # 사이트별 상대 빈도
        kdf["rank"] = range(1, len(kdf) + 1)
        keyword_frames.append(kdf[["site", "rank", "word", "count", "ratio"]])
    else:
        print(f"  ! {site}: tokens 컬럼이 없어 키워드 집계를 건너뜁니다.")

# ---------------- 저장 ----------------
reviews = pd.concat(review_frames, ignore_index=True)
reviews_path = os.path.join(OUT_DIR, "tableau_reviews.csv")
reviews.to_csv(reviews_path, index=False, encoding="utf-8-sig")
print(f"\n저장: {reviews_path}  ({reviews.shape[0]}행 x {reviews.shape[1]}열)")
print("  사이트별 행 수:")
print(reviews["site"].value_counts().to_string())

if keyword_frames:
    keywords = pd.concat(keyword_frames, ignore_index=True)
    keywords_path = os.path.join(OUT_DIR, "tableau_keywords.csv")
    keywords.to_csv(keywords_path, index=False, encoding="utf-8-sig")
    print(f"\n저장: {keywords_path}  ({keywords.shape[0]}행)")