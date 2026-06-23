from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd


DEFAULT_COURSE_JSON = (
    Path(__file__).resolve().parents[1]
    / "outputs"
    / "course-data-cleaned"
    / "ssu_time_courses_clean.json"
)
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "data"


def split_professors(value: str) -> list[str]:
    if not value:
        return []

    parts = re.split(r"[\n,/]+", str(value))
    cleaned: list[str] = []

    for part in parts:
        name = part.strip()
        name = re.sub(r"\s+", " ", name)
        name = name.replace("(팀티칭)", "").strip()
        if name and name not in cleaned:
            cleaned.append(name)

    return cleaned


def build_targets(course_json: Path) -> pd.DataFrame:
    courses = json.loads(course_json.read_text(encoding="utf-8"))
    grouped: dict[tuple[str, str], dict[str, object]] = {}

    for row in courses:
        course_name = str(row.get("course_name") or "").strip()
        if not course_name:
            continue

        for professor in split_professors(str(row.get("professor") or "")):
            key = (course_name, professor)
            item = grouped.setdefault(
                key,
                {
                    "course_name": course_name,
                    "professor": professor,
                    "course_codes": set(),
                    "course_groups": set(),
                    "completion_types": set(),
                    "row_count": 0,
                },
            )
            item["row_count"] = int(item["row_count"]) + 1
            item["course_codes"].add(str(row.get("course_code") or "").strip())
            item["course_groups"].add(str(row.get("course_group") or "").strip())
            item["completion_types"].add(str(row.get("completion_type") or "").strip())

    records = []
    for item in grouped.values():
        records.append(
            {
                "course_name": item["course_name"],
                "professor": item["professor"],
                "course_codes": "|".join(sorted(filter(None, item["course_codes"]))),
                "course_groups": "|".join(sorted(filter(None, item["course_groups"]))),
                "completion_types": "|".join(sorted(filter(None, item["completion_types"]))),
                "timetable_row_count": item["row_count"],
            }
        )

    return pd.DataFrame(records).sort_values(["course_name", "professor"]).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--course-json", type=Path, default=DEFAULT_COURSE_JSON)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    if not args.course_json.exists():
        raise FileNotFoundError(f"Course JSON not found: {args.course_json}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    targets = build_targets(args.course_json)

    csv_path = args.out_dir / "everytime_targets.csv"
    xlsx_path = args.out_dir / "everytime_targets.xlsx"

    targets.to_csv(csv_path, index=False, encoding="utf-8-sig")
    targets.to_excel(xlsx_path, index=False)

    print(f"Targets: {len(targets)}")
    print(f"Wrote: {csv_path}")
    print(f"Wrote: {xlsx_path}")


if __name__ == "__main__":
    main()
