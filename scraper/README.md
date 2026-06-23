# SSU-TIME Everytime Scraper

This scraper is designed for one-time collection of lecture reviews using the
course/professor list already cleaned for SSU-TIME.

Important:
- Use only an account you are allowed to use.
- Do not publish `.env`, `raw_reviews.jsonl`, or `reviews.xlsx`.
- Do not bypass CAPTCHA, MFA, blocks, or access restrictions.
- Keep crawling slow. The default delay is intentionally conservative.

## Setup

```powershell
cd scraper
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
copy .env.example .env
```

Edit `.env` and fill in your Everytime ID/password.

## 1. Build crawl targets

```powershell
python build_targets.py
```

This creates:

```text
data/everytime_targets.csv
data/everytime_targets.xlsx
```

Targets are unique by:

```text
course_name + professor
```

The full timetable rows are not deleted. The target file is only for crawling
Everytime lecture reviews.

## 2. Test with a small limit

```powershell
python scrape_everytime.py --limit 3 --headful
```

Use `--headful` while testing so you can handle login issues manually if needed.

If automatic login does not pass the login page, use manual login mode:

```powershell
python scrape_everytime.py --limit 3 --headful --manual-login
```

In manual login mode, log in by yourself in the opened browser window. The script
waits until the lecture search page is available, saves the browser session, and
then continues crawling.

## 3. Full crawl

```powershell
python scrape_everytime.py --headful
```

Outputs:

```text
data/raw_reviews.jsonl
data/reviews.xlsx
data/scrape_status.json
```

If the script stops, run it again. It skips targets that already have a final
status in `scrape_status.json`.

## API crawl mode

If you copy the Everytime API request from DevTools, API mode is easier than DOM
scraping.

Required API endpoints:

```text
https://api.everytime.kr/find/lecture/list/keyword
https://api.everytime.kr/find/lecture/article/list
```

Use one of these two session methods:

1. Put the Cookie header value in `.env`:

```env
EVERYTIME_COOKIE=_ga=...; x-et-device=...; etsid=...
```

2. Or save DevTools `Copy as cURL (bash)` output into:

```text
curl_find_lecture.txt
curl_article_list.txt
```

Then run a small test:

```powershell
python api_scrape_everytime.py --limit 3
```

Full API crawl:

```powershell
python api_scrape_everytime.py
```

Outputs:

```text
data/api_raw_reviews.jsonl
data/api_reviews.xlsx
data/api_scrape_status.json
```
