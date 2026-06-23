from __future__ import annotations

import argparse
import json
import os
import random
import re
import shlex
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv


FIND_LECTURE_URL = "https://api.everytime.kr/find/lecture/list/keyword"
ARTICLE_LIST_URL = "https://api.everytime.kr/find/lecture/article/list"

DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_TARGETS = DEFAULT_DATA_DIR / "everytime_targets.csv"
DEFAULT_STATUS = DEFAULT_DATA_DIR / "api_scrape_status.json"
DEFAULT_JSONL = DEFAULT_DATA_DIR / "api_raw_reviews.jsonl"
DEFAULT_XLSX = DEFAULT_DATA_DIR / "api_reviews.xlsx"
DEFAULT_FIND_CURL = Path(__file__).resolve().parent / "curl_find_lecture.txt"
DEFAULT_ARTICLE_CURL = Path(__file__).resolve().parent / "curl_article_list.txt"

FINAL_STATUSES = {"success", "no_reviews", "not_found"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).lower()


def target_key(course_name: str, professor: str) -> str:
    return f"{course_name}__{professor}"


def load_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_status(path: Path, status: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")


def random_delay(min_seconds: float, max_seconds: float) -> None:
    time.sleep(random.uniform(min_seconds, max_seconds))


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def export_xlsx(jsonl_path: Path, xlsx_path: Path) -> None:
    if not jsonl_path.exists():
        return
    rows = []
    with jsonl_path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    if rows:
        pd.DataFrame(rows).to_excel(xlsx_path, index=False)


def parse_curl(curl_text: str) -> dict[str, Any]:
    command = curl_text.replace("\\\n", " ")
    tokens = shlex.split(command, posix=True)
    parsed: dict[str, Any] = {"url": "", "headers": {}, "cookie": "", "data": ""}

    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "curl" and index + 1 < len(tokens):
            parsed["url"] = tokens[index + 1]
            index += 2
            continue
        if token in {"-H", "--header"} and index + 1 < len(tokens):
            header = tokens[index + 1]
            if ":" in header:
                key, value = header.split(":", 1)
                parsed["headers"][key.strip().lower()] = value.strip()
            index += 2
            continue
        if token in {"-b", "--cookie"} and index + 1 < len(tokens):
            parsed["cookie"] = tokens[index + 1]
            index += 2
            continue
        if token in {"--data-raw", "--data", "--data-binary", "-d"} and index + 1 < len(tokens):
            parsed["data"] = tokens[index + 1]
            index += 2
            continue
        index += 1

    return parsed


def load_curl(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"url": "", "headers": {}, "cookie": "", "data": ""}
    return parse_curl(path.read_text(encoding="utf-8"))


def build_headers(find_curl: dict[str, Any], article_curl: dict[str, Any]) -> dict[str, str]:
    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://everytime.kr",
        "referer": "https://everytime.kr/",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
        ),
    }

    for source in (find_curl, article_curl):
        for key in ["accept", "accept-language", "content-type", "origin", "referer", "user-agent"]:
            if source.get("headers", {}).get(key):
                headers[key] = source["headers"][key]

    cookie = os.getenv("EVERYTIME_COOKIE", "").strip()
    cookie = cookie or find_curl.get("cookie", "") or article_curl.get("cookie", "")
    if not cookie:
        raise RuntimeError(
            "No Everytime session cookie found. Put it in EVERYTIME_COOKIE in .env "
            "or save Copy as cURL output to curl_find_lecture.txt / curl_article_list.txt."
        )

    headers["cookie"] = cookie
    return headers


def post_form(session: requests.Session, url: str, headers: dict[str, str], data: dict[str, Any]) -> Any:
    response = session.post(url, headers=headers, data=data, timeout=20)
    if response.status_code in {401, 403}:
        raise RuntimeError(f"Session rejected by Everytime API: HTTP {response.status_code}")
    response.raise_for_status()
    return response.json()


def walk_json(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for item in value:
            yield from walk_json(item)


def get_any(row: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in row and row[key] not in {None, ""}:
            return row[key]
    return ""


def extract_lectures(payload: Any) -> list[dict[str, Any]]:
    lectures: list[dict[str, Any]] = []
    seen = set()

    for item in walk_json(payload):
        course_name = get_any(item, ["name", "lectureName", "courseName", "subjectName", "title"])
        professor = get_any(item, ["professor", "professorName", "teacher", "teacherName", "instructor"])
        lecture_id = get_any(item, ["id", "lectureId", "lecture_id"])
        if not course_name or not professor or not lecture_id:
            continue
        key = (str(course_name), str(professor), str(lecture_id))
        if key in seen:
            continue
        seen.add(key)
        lectures.append(item)

    return lectures


def lecture_matches(item: dict[str, Any], course_name: str, professor: str) -> bool:
    item_course = get_any(item, ["name", "lectureName", "courseName", "subjectName", "title"])
    item_professor = get_any(item, ["professor", "professorName", "teacher", "teacherName", "instructor"])
    return normalize_text(course_name) in normalize_text(item_course) and normalize_text(professor) in normalize_text(item_professor)


def find_lecture_id(
    session: requests.Session,
    headers: dict[str, str],
    course_name: str,
    professor: str,
    limit: int = 20,
) -> tuple[str, dict[str, Any] | None]:
    offset = 0
    best_partial: dict[str, Any] | None = None

    while offset < 100:
        payload = post_form(
            session,
            FIND_LECTURE_URL,
            headers,
            {
                "campusId": 0,
                "field": "name",
                "keyword": course_name,
                "limit": limit,
                "offset": offset,
            },
        )
        lectures = extract_lectures(payload)

        for item in lectures:
            if lecture_matches(item, course_name, professor):
                lecture_id = get_any(item, ["id", "lectureId", "lecture_id"])
                return str(lecture_id), item
            item_course = get_any(item, ["name", "lectureName", "courseName", "subjectName", "title"])
            if normalize_text(course_name) in normalize_text(item_course) and best_partial is None:
                best_partial = item

        if len(lectures) < limit:
            break
        offset += limit

    return "", best_partial


def extract_review_rows(payload: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen = set()

    for item in walk_json(payload):
        text = get_any(item, ["text", "content", "body", "article", "review"])
        if not text:
            continue
        text = str(text).strip()
        if len(text) < 5:
            continue
        review_id = get_any(item, ["id", "articleId", "reviewId"])
        key = str(review_id or text[:80])
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "review_id": review_id,
                "semester": get_any(item, ["semester", "term"]),
                "rating": get_any(item, ["rate", "rating", "star", "score"]),
                "review_text": text,
                "raw": item,
            }
        )

    return rows


def fetch_reviews(
    session: requests.Session,
    headers: dict[str, str],
    lecture_id: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    offset = 0
    rows: list[dict[str, Any]] = []
    seen = set()

    while offset < 1000:
        payload = post_form(
            session,
            ARTICLE_LIST_URL,
            headers,
            {"lectureId": lecture_id, "limit": limit, "offset": offset, "sort": "id"},
        )
        page_rows = extract_review_rows(payload)

        for row in page_rows:
            key = str(row.get("review_id") or row.get("review_text", "")[:80])
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)

        if len(page_rows) < limit:
            break
        offset += limit

    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", type=Path, default=DEFAULT_TARGETS)
    parser.add_argument("--status", type=Path, default=DEFAULT_STATUS)
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    parser.add_argument("--find-curl", type=Path, default=DEFAULT_FIND_CURL)
    parser.add_argument("--article-curl", type=Path, default=DEFAULT_ARTICLE_CURL)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()

    load_dotenv(Path(__file__).resolve().parent / ".env")

    if not args.targets.exists():
        raise FileNotFoundError(f"Targets not found. Run build_targets.py first: {args.targets}")

    min_delay = float(os.getenv("CRAWL_MIN_DELAY_SECONDS", "2.0"))
    max_delay = float(os.getenv("CRAWL_MAX_DELAY_SECONDS", "5.0"))

    headers = build_headers(load_curl(args.find_curl), load_curl(args.article_curl))
    targets = pd.read_csv(args.targets).to_dict("records")
    if args.limit is not None:
        targets = targets[: args.limit]

    status = load_status(args.status)
    session = requests.Session()

    for index, target in enumerate(targets, start=1):
        course_name = str(target["course_name"]).strip()
        professor = str(target["professor"]).strip()
        key = target_key(course_name, professor)
        previous = status.get(key, {})

        if not args.retry_failed and previous.get("status") in FINAL_STATUSES:
            print(f"[{index}/{len(targets)}] SKIP {key}: {previous.get('status')}")
            continue

        print(f"[{index}/{len(targets)}] API {key}")
        try:
            random_delay(min_delay, max_delay)
            lecture_id, matched = find_lecture_id(session, headers, course_name, professor)
            if not lecture_id:
                status[key] = {
                    "status": "not_found",
                    "message": "No lecture matched course_name + professor",
                    "updated_at": now_iso(),
                    "partial_match": matched,
                }
                save_status(args.status, status)
                print("  -> not_found")
                continue

            random_delay(min_delay, max_delay)
            reviews = fetch_reviews(session, headers, lecture_id)
            if not reviews:
                status[key] = {
                    "status": "no_reviews",
                    "lecture_id": lecture_id,
                    "message": "No reviews returned",
                    "review_count": 0,
                    "updated_at": now_iso(),
                    "matched_lecture": matched,
                }
                save_status(args.status, status)
                print(f"  -> no_reviews lecture_id={lecture_id}")
                continue

            output_rows = []
            for review_index, review in enumerate(reviews, start=1):
                raw = review.pop("raw", {})
                output_rows.append(
                    {
                        "course_name": course_name,
                        "professor": professor,
                        "lecture_id": lecture_id,
                        "review_index": review_index,
                        "semester": review.get("semester", ""),
                        "rating": review.get("rating", ""),
                        "review_text": review.get("review_text", ""),
                        "scraped_at": now_iso(),
                        "matched_lecture": matched,
                        "raw_review": raw,
                    }
                )

            append_jsonl(args.jsonl, output_rows)
            export_xlsx(args.jsonl, args.xlsx)
            status[key] = {
                "status": "success",
                "lecture_id": lecture_id,
                "review_count": len(output_rows),
                "updated_at": now_iso(),
                "matched_lecture": matched,
            }
            save_status(args.status, status)
            print(f"  -> success lecture_id={lecture_id} reviews={len(output_rows)}")
        except Exception as exc:
            status[key] = {
                "status": "error",
                "message": repr(exc),
                "updated_at": now_iso(),
            }
            save_status(args.status, status)
            print(f"  -> error {exc!r}")

    export_xlsx(args.jsonl, args.xlsx)


if __name__ == "__main__":
    main()
