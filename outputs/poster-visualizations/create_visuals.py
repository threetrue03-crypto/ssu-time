from __future__ import annotations

from pathlib import Path
import re

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager


BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "outputs" / "poster-visualizations"
FILES = {"A": OUT / "compare_A.txt", "B": OUT / "compare_B.txt"}

FONT_PATH = Path("C:/Windows/Fonts/malgun.ttf")
if FONT_PATH.exists():
    font_manager.fontManager.addfont(str(FONT_PATH))
    plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

FEATURE_LABELS = ["과제량", "팀플/발표", "시험비중", "난이도", "학점후함", "출석엄격", "분위기"]
VECTORS = {
    "A": [0.10, 0.10, 0.10, 0.15, 0.90, 0.10, 0.92],
    "B": [0.85, 0.85, 0.85, 0.82, 0.45, 0.75, 0.45],
}
LABELS = {"A": "비교군 A 부담 최소형", "B": "비교군 B 학습 몰입형"}
COLORS = {"A": "#35B6E8", "B": "#FF8F88"}
SOFT = {"A": "#BFEAF8", "B": "#FFD5D0"}


def read_log(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    return re.sub(r"\x1b\[[0-9;]*m", "", raw)


def parse_log(text: str) -> dict:
    result = {"candidate_count": 0, "profiles": 0, "course_rows": 0, "liberal_rows": 0, "plans": {}}
    for field, pattern in [
        ("course_rows", r"total course rows:\s*(\d+)"),
        ("liberal_rows", r"liberal auto-pool rows:\s*(\d+)"),
        ("profiles", r"course/professor profiles:\s*(\d+)"),
        ("candidate_count", r"accepted candidate plans:\s*(\d+)"),
    ]:
        match = re.search(pattern, text)
        if match:
            result[field] = int(match.group(1))

    matches = list(re.finditer(r"-\s*([ABC]).*?type=([\w-]+)\s+credits=(\d+)\s+score=([0-9.]+)", text))
    for index, match in enumerate(matches):
        label = match.group(1)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end() : end]
        lecture_fits = [float(value) for value in re.findall(r"lecture_fit=([0-9.]+)", block)]
        keyword_fits = [float(value) for value in re.findall(r"keyword_fit=([0-9.]+)", block)]
        reviews = [int(value) for value in re.findall(r"reviews=(\d+)", block)]
        result["plans"][label] = {
            "type": match.group(2),
            "credits": int(match.group(3)),
            "score": float(match.group(4)),
            "lecture_avg": float(np.mean(lecture_fits)) if lecture_fits else 0,
            "keyword_avg": float(np.mean(keyword_fits)) if keyword_fits else 0,
            "review_sum": sum(reviews),
            "course_count": len(lecture_fits),
            "liberal_count": sum(1 for value in keyword_fits if abs(value - 0.5) < 1e-6),
        }
    return result


def build_summary(parsed: dict[str, dict]) -> dict[str, dict]:
    summary = {}
    for key, data in parsed.items():
        plan = data["plans"].get("A") or next(iter(data["plans"].values()), {})
        summary[key] = {
            "score": plan.get("score", 0) * 100,
            "lecture": plan.get("lecture_avg", 0) * 100,
            "keyword": plan.get("keyword_avg", 0) * 100,
            "candidates": data.get("candidate_count") or 0,
            "profiles": data.get("profiles") or 0,
            "course_rows": data.get("course_rows") or 0,
            "liberal_rows": data.get("liberal_rows") or 0,
            "review_sum": plan.get("review_sum", 0),
            "liberal_count": plan.get("liberal_count", 0),
        }
    return summary


def style_axes(ax):
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_axisbelow(True)


def save_combined(summary: dict[str, dict]):
    fig = plt.figure(figsize=(15, 10), dpi=180, facecolor="#DDF5FB")
    grid = fig.add_gridspec(
        2,
        2,
        height_ratios=[1.05, 1.0],
        wspace=0.20,
        hspace=0.50,
        top=0.86,
        bottom=0.07,
    )
    fig.suptitle("SSU-TIME 비교 실험 시각화", fontsize=25, fontweight="bold", color="#132F4C", y=0.985)
    fig.text(
        0.5,
        0.932,
        "동일한 전공 4과목 · 18학점 · 교양 랜덤 조건에서 사용자 니즈 벡터만 변경",
        ha="center",
        fontsize=12.5,
        color="#405A70",
    )

    angles = np.linspace(0, 2 * np.pi, len(FEATURE_LABELS), endpoint=False).tolist()
    angles += angles[:1]

    ax = fig.add_subplot(grid[0, 0], polar=True, facecolor="white")
    for key in ["A", "B"]:
        values = VECTORS[key] + VECTORS[key][:1]
        ax.plot(angles, values, color=COLORS[key], linewidth=2.8, label=LABELS[key])
        ax.fill(angles, values, color=COLORS[key], alpha=0.17)
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(FEATURE_LABELS, fontsize=10, color="#132F4C")
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.50", "0.75", "1.00"], fontsize=8, color="#6B7F90")
    ax.set_ylim(0, 1)
    ax.grid(color="#CFE8F1")
    ax.set_title("사용자 니즈 벡터", pad=24, fontsize=16, fontweight="bold", color="#132F4C")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.16), ncols=2, frameon=False, fontsize=9)

    ax = fig.add_subplot(grid[0, 1], facecolor="white")
    metrics = ["최종 적합도", "강의평 적합도", "교양 적합도"]
    x = np.arange(len(metrics))
    width = 0.34
    a_values = [summary["A"]["score"], summary["A"]["lecture"], summary["A"]["keyword"]]
    b_values = [summary["B"]["score"], summary["B"]["lecture"], summary["B"]["keyword"]]
    bars_a = ax.bar(x - width / 2, a_values, width, color=COLORS["A"], label="비교군 A")
    bars_b = ax.bar(x + width / 2, b_values, width, color=COLORS["B"], label="비교군 B")
    ax.set_ylim(0, 100)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=10)
    ax.set_ylabel("점수 (0-100)", fontsize=10)
    ax.set_title("추천 결과 점수 (A안 기준)", fontsize=16, fontweight="bold", color="#132F4C", pad=14)
    ax.grid(axis="y", color="#E5F4F8")
    ax.legend(frameon=False)
    for bars in [bars_a, bars_b]:
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                height + 1.3,
                f"{height:.1f}",
                ha="center",
                fontsize=8.5,
                fontweight="bold",
                color="#132F4C",
            )
    style_axes(ax)

    ax = fig.add_subplot(grid[1, 0], facecolor="white")
    scale_labels = ["과목 DB", "교양 후보풀", "강의평 프로필", "가능 조합 A", "가능 조합 B"]
    scale_values = [
        summary["A"]["course_rows"],
        summary["A"]["liberal_rows"],
        summary["A"]["profiles"],
        summary["A"]["candidates"],
        summary["B"]["candidates"],
    ]
    scale_colors = ["#8ED7EF", "#A8E6E2", "#B9D1FF", COLORS["A"], COLORS["B"]]
    y = np.arange(len(scale_labels))
    ax.barh(y, scale_values, color=scale_colors)
    ax.set_yticks(y)
    ax.set_yticklabels(scale_labels, fontsize=10)
    ax.invert_yaxis()
    ax.set_xscale("log")
    ax.set_xlabel("개수 (log scale)", fontsize=10)
    ax.set_title("백엔드 탐색 규모", fontsize=16, fontweight="bold", color="#132F4C", pad=14)
    ax.grid(axis="x", color="#E5F4F8")
    for yy, value in zip(y, scale_values):
        ax.text(max(value, 1) * 1.08, yy, f"{value:,}", va="center", fontsize=9, fontweight="bold", color="#132F4C")
    style_axes(ax)

    ax = fig.add_subplot(grid[1, 1], facecolor="white")
    ax.axis("off")
    ax.set_title("비교군별 해석", fontsize=16, fontweight="bold", color="#132F4C", pad=14)
    card_data = [
        ("A", "부담 최소형", "과제·팀플·시험 부담을 낮추고\n학점 후함과 편한 분위기를 선호"),
        ("B", "학습 몰입형", "시험 중심·난이도 있는 수업과\n체계적인 강의 운영을 선호"),
    ]
    for index, (key, title, description) in enumerate(card_data):
        x0 = 0.06 + index * 0.47
        y0 = 0.54
        ax.add_patch(plt.Rectangle((x0, y0), 0.40, 0.33, transform=ax.transAxes, facecolor=SOFT[key], edgecolor="none"))
        ax.text(x0 + 0.03, y0 + 0.25, f"비교군 {key}", transform=ax.transAxes, fontsize=13, fontweight="bold", color="#132F4C")
        ax.text(x0 + 0.03, y0 + 0.18, title, transform=ax.transAxes, fontsize=18, fontweight="bold", color=COLORS[key])
        ax.text(x0 + 0.03, y0 + 0.075, description, transform=ax.transAxes, fontsize=10.5, color="#334B5F", linespacing=1.35)
        ax.text(x0 + 0.03, y0 - 0.055, f"최종 적합도 {summary[key]['score']:.1f}점", transform=ax.transAxes, fontsize=11, fontweight="bold", color="#132F4C")
        ax.text(x0 + 0.03, y0 - 0.135, f"강의평 적합도 {summary[key]['lecture']:.1f}점", transform=ax.transAxes, fontsize=10, color="#405A70")
        ax.text(x0 + 0.03, y0 - 0.215, f"탐색 조합 {summary[key]['candidates']:,}개", transform=ax.transAxes, fontsize=10, color="#405A70")
    ax.text(
        0.06,
        0.08,
        "해석: 같은 전공·학점 조건에서도 사용자 니즈 벡터가 달라지면\n강의평 벡터와의 유사도 계산 결과가 달라져 추천 시안이 달라진다.",
        transform=ax.transAxes,
        fontsize=11.5,
        color="#132F4C",
        fontweight="bold",
        linespacing=1.4,
    )

    fig.savefig(OUT / "ssu_time_comparison_panel.png", bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(OUT / "ssu_time_comparison_panel.svg", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def save_individual(summary: dict[str, dict]):
    angles = np.linspace(0, 2 * np.pi, len(FEATURE_LABELS), endpoint=False).tolist()
    angles += angles[:1]

    fig = plt.figure(figsize=(7, 7), dpi=180, facecolor="#DDF5FB")
    ax = fig.add_subplot(111, polar=True, facecolor="white")
    for key in ["A", "B"]:
        values = VECTORS[key] + VECTORS[key][:1]
        ax.plot(angles, values, color=COLORS[key], linewidth=2.8, label=LABELS[key])
        ax.fill(angles, values, color=COLORS[key], alpha=0.17)
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(FEATURE_LABELS, fontsize=9)
    ax.set_ylim(0, 1)
    ax.grid(color="#CFE8F1")
    ax.set_title("사용자 니즈 벡터 비교", fontsize=16, fontweight="bold", color="#132F4C", pad=22)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.18), ncols=2, frameon=False)
    fig.savefig(OUT / "need_vector_radar.png", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5), dpi=180, facecolor="#DDF5FB")
    ax.set_facecolor("white")
    metrics = ["최종 적합도", "강의평 적합도", "교양 적합도"]
    x = np.arange(len(metrics))
    width = 0.34
    ax.bar(x - width / 2, [summary["A"]["score"], summary["A"]["lecture"], summary["A"]["keyword"]], width, color=COLORS["A"], label="비교군 A")
    ax.bar(x + width / 2, [summary["B"]["score"], summary["B"]["lecture"], summary["B"]["keyword"]], width, color=COLORS["B"], label="비교군 B")
    ax.set_ylim(0, 100)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.set_title("추천 결과 점수 비교", fontsize=16, fontweight="bold", color="#132F4C", pad=14)
    ax.grid(axis="y", color="#E5F4F8")
    ax.legend(frameon=False)
    style_axes(ax)
    fig.savefig(OUT / "result_score_bars.png", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def main():
    parsed = {key: parse_log(read_log(path)) for key, path in FILES.items()}
    summary = build_summary(parsed)
    save_combined(summary)
    save_individual(summary)
    print(summary)


if __name__ == "__main__":
    main()
