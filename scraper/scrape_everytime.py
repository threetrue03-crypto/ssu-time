from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright


BASE_URL = "https://everytime.kr/"
LECTURE_URL = "https://everytime.kr/lecture"
LOGIN_URL = "https://account.everytime.kr/login"

XPATH = {
    "home_login_button": "/html/body/div/aside/div[2]/div[1]/a[1]",
    "login_id": "/html/body/div[1]/div/form/div[1]/input[1]",
    "login_password": "/html/body/div[1]/div/form/div[1]/input[2]",
    "login_submit": "/html/body/div[1]/div/form/input",
    "lecture_menu": "//*[@id='menu']/li[3]/a",
    "course_search": "/html/body/div/div/div[1]/div/form/input[1]",
    "no_reviews": "/html/body/div/div/div[2]/div/section[2]/p",
    "review_more": "/html/body/div/div/div[2]/div/section[2]/div[2]/a",
    "review_text_container": "/html/body/div/div/div[2]/div/div[2]/div/div[2]",
}

DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_TARGETS = DEFAULT_DATA_DIR / "everytime_targets.csv"
DEFAULT_STATUS = DEFAULT_DATA_DIR / "scrape_status.json"
DEFAULT_JSONL = DEFAULT_DATA_DIR / "raw_reviews.jsonl"
DEFAULT_XLSX = DEFAULT_DATA_DIR / "reviews.xlsx"
DEFAULT_STORAGE_STATE = DEFAULT_DATA_DIR / "storage_state.json"
DEFAULT_DEBUG_SCREENSHOT = DEFAULT_DATA_DIR / "login_failed.png"

FINAL_STATUSES = {"success", "no_reviews", "not_found"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_status(path: Path, status: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")


def target_key(course_name: str, professor: str) -> str:
    return f"{course_name}__{professor}"


def random_delay(min_seconds: float, max_seconds: float) -> None:
    time.sleep(random.uniform(min_seconds, max_seconds))


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def xpath(page: Page, name: str):
    return page.locator(f"xpath={XPATH[name]}")


def fill_first_visible(page: Page, selectors: list[str], value: str, timeout_ms: int = 5000) -> None:
    for selector in selectors:
        locator = page.locator(selector)
        try:
            count = locator.count()
        except Exception:
            count = 0

        for index in range(count):
            item = locator.nth(index)
            try:
                if item.is_visible(timeout=700):
                    item.fill(value, timeout=timeout_ms)
                    return
            except Exception:
                continue

    raise RuntimeError(f"No visible input matched selectors: {selectors}")


def click_first_visible(page: Page, selectors: list[str], timeout_ms: int = 5000) -> None:
    for selector in selectors:
        locator = page.locator(selector)
        try:
            count = locator.count()
        except Exception:
            count = 0

        for index in range(count):
            item = locator.nth(index)
            try:
                if item.is_visible(timeout=700):
                    item.click(timeout=timeout_ms)
                    return
            except Exception:
                continue

    raise RuntimeError(f"No visible button matched selectors: {selectors}")


def safe_text(locator, timeout_ms: int = 1200) -> str:
    try:
        if locator.count() == 0:
            return ""
        return locator.first.inner_text(timeout=timeout_ms).strip()
    except Exception:
        return ""


def wait_until_lecture_search(page: Page, timeout_ms: int = 120000) -> None:
    deadline = time.time() + (timeout_ms / 1000)
    last_error: Exception | None = None

    while time.time() < deadline:
        try:
            page.goto(LECTURE_URL, wait_until="domcontentloaded")
            page.wait_for_selector(f"xpath={XPATH['course_search']}", timeout=5000)
            return
        except Exception as exc:
            last_error = exc
            page.wait_for_timeout(1200)

    DEFAULT_DEBUG_SCREENSHOT.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(DEFAULT_DEBUG_SCREENSHOT), full_page=True)
    raise RuntimeError(
        "Login did not reach the lecture search page. If CAPTCHA/MFA/blocking "
        "appears, handle it manually or stop. This script does not bypass access "
        f"controls. Current URL: {page.url}. Debug screenshot: {DEFAULT_DEBUG_SCREENSHOT}"
    ) from last_error


def login(page: Page, storage_state_path: Path, manual_login: bool = False) -> None:
    page.goto(BASE_URL, wait_until="domcontentloaded")

    try:
        page.goto(LECTURE_URL, wait_until="domcontentloaded")
        page.wait_for_selector(f"xpath={XPATH['course_search']}", timeout=2500)
        return
    except PlaywrightTimeoutError:
        pass

    if manual_login:
        page.goto(LOGIN_URL, wait_until="domcontentloaded")
        print("Manual login mode: log in in the opened browser window.")
        print("Complete MFA/2-step verification yourself.")
        print("After you can see the Everytime home or lecture page, return here and press Enter.")
        input("Press Enter after manual login is complete...")
        wait_until_lecture_search(page)
        page.context.storage_state(path=str(storage_state_path))
        return

    user_id = os.getenv("EVERYTIME_ID")
    password = os.getenv("EVERYTIME_PASSWORD")

    if not user_id or not password:
        raise RuntimeError("Set EVERYTIME_ID and EVERYTIME_PASSWORD in scraper/.env")

    page.goto(BASE_URL, wait_until="domcontentloaded")
    try:
        xpath(page, "home_login_button").click(timeout=5000)
    except PlaywrightTimeoutError:
        page.goto(LOGIN_URL, wait_until="domcontentloaded")

    fill_first_visible(
        page,
        [
            f"xpath={XPATH['login_id']}",
            "input[placeholder='아이디']",
            "input[name='userid']",
            "input[name='id']",
            "input[type='text']",
        ],
        user_id,
    )
    fill_first_visible(
        page,
        [
            f"xpath={XPATH['login_password']}",
            "input[placeholder='비밀번호']",
            "input[name='password']",
            "input[type='password']",
        ],
        password,
    )
    click_first_visible(
        page,
        [
            f"xpath={XPATH['login_submit']}",
            "input[type='submit']",
            "button[type='submit']",
            "button:has-text('로그인')",
            "input[value*='로그인']",
        ],
    )

    try:
        page.wait_for_load_state("domcontentloaded", timeout=12000)
    except PlaywrightTimeoutError:
        pass

    wait_until_lecture_search(page, timeout_ms=20000)

    page.context.storage_state(path=str(storage_state_path))


def open_lecture_page(page: Page) -> None:
    try:
        xpath(page, "lecture_menu").click(timeout=3000)
        page.wait_for_selector(f"xpath={XPATH['course_search']}", timeout=5000)
    except Exception:
        page.goto(LECTURE_URL, wait_until="domcontentloaded")
        page.wait_for_selector(f"xpath={XPATH['course_search']}", timeout=8000)


def search_course(page: Page, course_name: str) -> None:
    search = xpath(page, "course_search")
    search.fill("")
    search.fill(course_name)
    search.press("Enter")
    page.wait_for_timeout(1400)


def click_matching_result(page: Page, course_name: str, professor: str) -> bool:
    # Prefer clickable links/cards that contain both course and professor text.
    selectors = ["a", "article", "li", "div"]

    for selector in selectors:
        locator = page.locator(selector).filter(has_text=course_name).filter(has_text=professor)
        try:
            count = min(locator.count(), 12)
        except Exception:
            count = 0

        for index in range(count):
            item = locator.nth(index)
            try:
                if not item.is_visible(timeout=500):
                    continue
                text = item.inner_text(timeout=500)
                if course_name not in text or professor not in text:
                    continue
                item.click(timeout=2500)
                page.wait_for_timeout(1200)
                return True
            except Exception:
                continue

    return False


def has_no_reviews(page: Page) -> bool:
    text = safe_text(xpath(page, "no_reviews"))
    return "아직 등록된 강의평이 없습니다" in text


def click_more_reviews(page: Page, max_clicks: int = 20) -> int:
    clicks = 0

    for _ in range(max_clicks):
        more = xpath(page, "review_more")
        try:
            if more.count() == 0 or not more.first.is_visible(timeout=800):
                break
            more.first.click(timeout=2500)
            clicks += 1
            page.wait_for_timeout(random.randint(700, 1300))
        except Exception:
            break

    return clicks


def split_review_text(raw_text: str) -> list[str]:
    text = raw_text.strip()
    if not text:
        return []

    # Everytime review pages often separate review blocks with blank lines or star lines.
    chunks = re.split(r"\n\s*\n+", text)
    cleaned = []
    for chunk in chunks:
        value = re.sub(r"\n{3,}", "\n\n", chunk).strip()
        if len(value) >= 20 and value not in cleaned:
            cleaned.append(value)

    return cleaned or [text]


def collect_reviews(page: Page) -> list[str]:
    container = xpath(page, "review_text_container")

    try:
        if container.count() > 0:
            texts = container.first.evaluate(
                """
                (node) => {
                  const children = Array.from(node.children || []);
                  const blocks = children
                    .map((el) => (el.innerText || '').trim())
                    .filter((text) => text.length >= 20);
                  if (blocks.length) return blocks;
                  const text = (node.innerText || '').trim();
                  return text ? [text] : [];
                }
                """
            )
            result: list[str] = []
            for text in texts:
                for chunk in split_review_text(text):
                    if chunk not in result:
                        result.append(chunk)
            return result
    except Exception:
        pass

    body_text = safe_text(page.locator("body"), timeout_ms=2500)
    return split_review_text(body_text)


def scrape_target(
    page: Page,
    target: dict[str, Any],
    min_delay: float,
    max_delay: float,
) -> tuple[str, list[dict[str, Any]], str]:
    course_name = str(target["course_name"]).strip()
    professor = str(target["professor"]).strip()

    open_lecture_page(page)
    random_delay(min_delay, max_delay)
    search_course(page, course_name)
    random_delay(min_delay, max_delay)

    if not click_matching_result(page, course_name, professor):
        return "not_found", [], "No search result matched course_name + professor"

    random_delay(min_delay, max_delay)

    if has_no_reviews(page):
        return "no_reviews", [], "No reviews"

    more_clicks = click_more_reviews(page)
    reviews = collect_reviews(page)

    rows = [
        {
            "course_name": course_name,
            "professor": professor,
            "review_index": index + 1,
            "review_text": review,
            "source_url": page.url,
            "scraped_at": now_iso(),
            "more_clicks": more_clicks,
        }
        for index, review in enumerate(reviews)
    ]

    if not rows:
        return "no_reviews", [], "No review text collected"

    return "success", rows, f"Collected {len(rows)} review blocks"


def export_xlsx(jsonl_path: Path, xlsx_path: Path) -> None:
    if not jsonl_path.exists():
        return

    rows = []
    with jsonl_path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    if not rows:
        return

    pd.DataFrame(rows).to_excel(xlsx_path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", type=Path, default=DEFAULT_TARGETS)
    parser.add_argument("--status", type=Path, default=DEFAULT_STATUS)
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    parser.add_argument("--storage-state", type=Path, default=DEFAULT_STORAGE_STATE)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--headful", action="store_true")
    parser.add_argument("--manual-login", action="store_true")
    parser.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()

    load_dotenv(Path(__file__).resolve().parent / ".env")

    if not args.targets.exists():
        raise FileNotFoundError(f"Targets file not found. Run build_targets.py first: {args.targets}")

    min_delay = float(os.getenv("CRAWL_MIN_DELAY_SECONDS", "2.0"))
    max_delay = float(os.getenv("CRAWL_MAX_DELAY_SECONDS", "5.0"))

    targets = pd.read_csv(args.targets).to_dict("records")
    if args.limit is not None:
        targets = targets[: args.limit]

    status = load_status(args.status)
    args.status.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headful)
        context_kwargs = {}
        if args.storage_state.exists():
            context_kwargs["storage_state"] = str(args.storage_state)
        context = browser.new_context(**context_kwargs)
        page = context.new_page()

        login(page, args.storage_state, manual_login=args.manual_login)

        for index, target in enumerate(targets, start=1):
            course_name = str(target["course_name"]).strip()
            professor = str(target["professor"]).strip()
            key = target_key(course_name, professor)
            previous = status.get(key, {})

            if (
                not args.retry_failed
                and previous.get("status") in FINAL_STATUSES
            ):
                print(f"[{index}/{len(targets)}] SKIP {key}: {previous.get('status')}")
                continue

            print(f"[{index}/{len(targets)}] SCRAPE {key}")
            try:
                state, rows, message = scrape_target(page, target, min_delay, max_delay)
                append_jsonl(args.jsonl, rows)
                status[key] = {
                    "status": state,
                    "message": message,
                    "review_count": len(rows),
                    "updated_at": now_iso(),
                }
                save_status(args.status, status)
                export_xlsx(args.jsonl, args.xlsx)
                print(f"  -> {state}: {message}")
            except Exception as exc:
                status[key] = {
                    "status": "error",
                    "message": repr(exc),
                    "review_count": 0,
                    "updated_at": now_iso(),
                }
                save_status(args.status, status)
                print(f"  -> error: {exc!r}")

        context.close()
        browser.close()

    export_xlsx(args.jsonl, args.xlsx)


if __name__ == "__main__":
    main()
