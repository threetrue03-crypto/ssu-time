from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from PIL import Image


BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "outputs" / "final-poster"
ASSETS = OUT / "assets"
VIS = BASE / "outputs" / "poster-visualizations"

FONT_PATH = Path("C:/Windows/Fonts/malgun.ttf")
if FONT_PATH.exists():
    font_manager.fontManager.addfont(str(FONT_PATH))
    plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

NAVY = "#14324F"
SKY = "#DDF5FB"
BLUE = "#35B6E8"
RED = "#FF8A84"
MINT = "#A9E6E2"
YELLOW = "#FFE0A3"
PURPLE = "#D9CBFF"
LINE = "#BFEAF8"
GRAY = "#536B80"
WHITE = "#FFFFFF"


def add_card(fig, x, y, w, h, title, title_size=18):
    ax = fig.add_axes([x, y, w, h])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    patch = FancyBboxPatch(
        (0, 0),
        1,
        1,
        boxstyle="round,pad=0.012,rounding_size=0.026",
        facecolor=WHITE,
        edgecolor="none",
        transform=ax.transAxes,
        zorder=-1,
    )
    ax.add_patch(patch)
    ax.text(0.04, 0.94, title, fontsize=title_size, fontweight="bold", color=NAVY, va="top")
    return ax


def text_block(ax, x, y, lines, size=11.5, color="#1F2F3D", weight="normal", line_gap=0.07):
    cursor = y
    for line in lines:
        ax.text(x, cursor, line, fontsize=size, color=color, fontweight=weight, va="top", ha="left")
        cursor -= line_gap
    return cursor


def bullet(ax, x, y, title, body, color=BLUE, size=10.8):
    ax.text(x, y, "•", fontsize=size + 3, color=color, fontweight="bold", va="top")
    ax.text(x + 0.035, y, title, fontsize=size, color=NAVY, fontweight="bold", va="top")
    ax.text(x + 0.035, y - 0.064, body, fontsize=size - 0.3, color="#354D61", va="top", linespacing=1.28)


def image_box(ax, path: Path, x, y, w, h, label=None, border=True):
    image = Image.open(path).convert("RGBA")
    iw, ih = image.size
    box_ratio = w / h
    img_ratio = iw / ih
    if img_ratio > box_ratio:
        draw_w = w
        draw_h = w / img_ratio
    else:
        draw_h = h
        draw_w = h * img_ratio
    x0 = x + (w - draw_w) / 2
    y0 = y + (h - draw_h) / 2
    if border:
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.004,rounding_size=0.018",
                facecolor="#F7FCFF",
                edgecolor=LINE,
                linewidth=1.2,
                transform=ax.transAxes,
                zorder=0,
            )
        )
    ax.imshow(image, extent=[x0, x0 + draw_w, y0, y0 + draw_h], transform=ax.transAxes, zorder=1)
    if label:
        ax.text(x + 0.02, y + h - 0.035, label, fontsize=9.2, color=NAVY, fontweight="bold", va="top", zorder=2)


def mini_metric(ax, x, y, label, value, color):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            0.28,
            0.13,
            boxstyle="round,pad=0.008,rounding_size=0.025",
            facecolor=color,
            edgecolor="none",
            alpha=0.75,
            transform=ax.transAxes,
        )
    )
    ax.text(x + 0.03, y + 0.086, label, fontsize=9.3, color=NAVY, fontweight="bold", va="top")
    ax.text(x + 0.03, y + 0.036, value, fontsize=13, color=NAVY, fontweight="bold", va="bottom")


def flow_box(ax, x, y, w, h, label, color):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.01,rounding_size=0.03",
            facecolor=color,
            edgecolor="none",
            transform=ax.transAxes,
        )
    )
    ax.text(x + w / 2, y + h / 2, label, fontsize=10.4, color=NAVY, fontweight="bold", ha="center", va="center")


def arrow(ax, start, end):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=13,
            color="#6CAFC8",
            linewidth=1.5,
            transform=ax.transAxes,
        )
    )


def create_poster():
    # A1 portrait: 594 x 841 mm = 23.39 x 33.11 inch.
    fig = plt.figure(figsize=(23.386, 33.110), dpi=170, facecolor=SKY)

    # Header
    fig.text(0.04, 0.965, "SSU-TIME", fontsize=58, fontweight="bold", color=NAVY, va="top")
    fig.text(
        0.04,
        0.922,
        "강의평 기반 맞춤형 시간표 추천 시스템",
        fontsize=31,
        fontweight="bold",
        color=NAVY,
        va="top",
    )
    fig.text(
        0.04,
        0.891,
        "사용자 니즈 벡터와 강의평 벡터의 유사도 분석을 활용한 2026학년도 1학기 시간표 자동 생성",
        fontsize=15.5,
        color="#425E73",
    )
    fig.text(
        0.04,
        0.866,
        "팀명: 너시간표내꺼   |   조세진 · 박시우 · 안민기 · 윤서준 · 이동연   |   AI소프트웨어학부",
        fontsize=12.8,
        color="#425E73",
    )
    fig.text(0.04, 0.845, "고급AI수학 · 김창훈 교수님 · 2026.06.18", fontsize=12.8, color="#425E73")
    fig.text(0.72, 0.955, "너시간표내꺼", fontsize=34, fontweight="bold", color=NAVY, ha="left", va="top")
    ax_mascot = fig.add_axes([0.855, 0.857, 0.105, 0.12])
    ax_mascot.axis("off")
    ax_mascot.imshow(Image.open(ASSETS / "mascot_lab.png").convert("RGBA"))

    # Column geometry
    gap = 0.018
    x1, w = 0.035, 0.300
    x2 = x1 + w + gap
    x3 = x2 + w + gap
    top = 0.825

    intro = add_card(fig, x1, 0.705, w, 0.120, "INTRODUCTION")
    text_block(
        intro,
        0.04,
        0.80,
        [
            "대학생이 시간표를 구성할 때는 단순한 시간 충돌뿐 아니라",
            "교수자의 강의 방식, 과제·시험 부담, 출석 기준, 학점 부여",
            "방식, 수업 분위기까지 함께 고려해야 한다.",
            "",
            "SSU-TIME은 과목 DB와 강의평 데이터를 결합하고 사용자의",
            "선호를 수치화하여 맞춤형 시간표 시안을 자동으로 생성한다.",
        ],
        size=10.6,
        line_gap=0.105,
    )

    goals = add_card(fig, x1, 0.545, w, 0.145, "PROJECT GOALS")
    bullet(goals, 0.04, 0.80, "과목·강의평 DB 결합", "수업 시간, 학점, 이수 구분, 교수자 정보를 강의평과 매칭한다.", BLUE)
    bullet(goals, 0.04, 0.56, "사용자 니즈 벡터화", "질문지 응답을 과제량, 시험비중, 난이도 등 7차원 벡터로 변환한다.", RED)
    bullet(goals, 0.04, 0.32, "맞춤형 시간표 생성", "벡터 유사도, 시간 충돌, 목표 학점을 함께 고려해 시안을 추천한다.", "#56C7BE")

    data = add_card(fig, x1, 0.415, w, 0.115, "DATASET")
    mini_metric(data, 0.04, 0.62, "과목 DB", "401개", "#BFEAF8")
    mini_metric(data, 0.36, 0.62, "교양 후보풀", "309개", "#C7EFEA")
    mini_metric(data, 0.68, 0.62, "강의평 프로필", "225개", "#D9CBFF")
    data.text(0.04, 0.43, "주요 컬럼: 과목명, 교수명, 이수 구분, 학점, 수업 시간, 강의실, 강의평, 별점, 리뷰 수", fontsize=10.2, color="#354D61", va="top")
    data.text(0.04, 0.24, "과목-교수 조합별 강의평을 분석하여 강의 특성 벡터를 생성하였다.", fontsize=10.2, color="#354D61", va="top")

    model = add_card(fig, x1, 0.170, w, 0.230, "LINEAR ALGEBRA MODEL")
    model.text(0.04, 0.80, "사용자 니즈 벡터와 강의평 벡터", fontsize=12, fontweight="bold", color=NAVY)
    model.text(0.07, 0.68, r"$\mathbf{u}=(u_1,u_2,\ldots,u_7)$", fontsize=24, color=NAVY)
    model.text(0.07, 0.56, r"$\mathbf{l}=(l_1,l_2,\ldots,l_7)$", fontsize=24, color=NAVY)
    model.text(0.04, 0.42, "강의평 적합도는 벡터의 방향과 거리 정보를 함께 사용한다.", fontsize=10.5, color="#354D61")
    model.text(0.07, 0.29, r"$\cos\theta=\frac{\mathbf{u}\cdot\mathbf{l}}{\|\mathbf{u}\|\|\mathbf{l}\|}$", fontsize=28, color=NAVY)
    model.text(0.04, 0.14, "최종 추천 점수", fontsize=12, fontweight="bold", color=NAVY)
    model.text(
        0.045,
        0.065,
        r"$S(T)=0.32S_{review}+0.12S_{time}+0.12S_{dayoff}$",
        fontsize=17.0,
        color=NAVY,
    )
    model.text(
        0.205,
        0.005,
        r"$+\,0.09S_{keyword}+0.35S_{credit}$",
        fontsize=17.0,
        color=NAVY,
    )

    conclusion = add_card(fig, x1, 0.035, w, 0.120, "CONCLUSION")
    text_block(
        conclusion,
        0.04,
        0.80,
        [
            "동일한 전공 과목과 목표 학점 조건에서도 사용자 니즈 벡터가",
            "달라지면 강의평 벡터와의 유사도 계산 결과가 달라져 추천",
            "시안이 변화하였다.",
            "",
            "이를 통해 선형대수 기반 벡터 유사도 계산이 개인화된 시간표",
            "추천 시스템에 활용될 수 있음을 확인하였다.",
        ],
        size=10.6,
        line_gap=0.108,
    )

    pipeline = add_card(fig, x2, 0.695, w, 0.130, "SYSTEM PIPELINE")
    flow_box(pipeline, 0.04, 0.56, 0.17, 0.20, "과목 DB", "#BFEAF8")
    flow_box(pipeline, 0.04, 0.25, 0.17, 0.20, "강의평 DB", "#D9CBFF")
    flow_box(pipeline, 0.29, 0.40, 0.18, 0.22, "벡터화", "#C7EFEA")
    flow_box(pipeline, 0.55, 0.40, 0.18, 0.22, "유사도\n계산", "#FFE0A3")
    flow_box(pipeline, 0.80, 0.40, 0.16, 0.22, "A/B/C\n시안", "#FFD4D0")
    arrow(pipeline, (0.21, 0.66), (0.29, 0.53))
    arrow(pipeline, (0.21, 0.35), (0.29, 0.47))
    arrow(pipeline, (0.47, 0.51), (0.55, 0.51))
    arrow(pipeline, (0.73, 0.51), (0.80, 0.51))

    flow = add_card(fig, x2, 0.385, w, 0.295, "WEB APP FLOW")
    image_box(flow, ASSETS / "home.png", 0.035, 0.45, 0.18, 0.43, "첫 화면")
    image_box(flow, ASSETS / "course_select.png", 0.225, 0.45, 0.18, 0.43, "과목 선택")
    image_box(flow, ASSETS / "needs_A_1.png", 0.415, 0.45, 0.18, 0.43, "니즈 입력")
    image_box(flow, ASSETS / "loading.png", 0.605, 0.45, 0.18, 0.43, "로딩")
    image_box(flow, ASSETS / "result_A_1.png", 0.795, 0.45, 0.17, 0.43, "결과")
    flow.text(0.05, 0.30, "사용자는 전공 과목을 직접 선택하고, 목표 학점과 수업 선호를 질문지로 입력한다.", fontsize=10.5, color="#354D61")
    flow.text(0.05, 0.20, "백엔드는 강의평 벡터와 사용자 니즈 벡터를 비교하여 시간 충돌이 없는 시간표 조합을 생성한다.", fontsize=10.5, color="#354D61")
    flow.text(0.05, 0.10, "최종적으로 적합도 높은 시간표 시안을 A/B/C로 제시하고 추천 근거를 함께 제공한다.", fontsize=10.5, color="#354D61")

    needs = add_card(fig, x2, 0.035, w, 0.335, "QUESTIONNAIRE SETTINGS")
    image_box(needs, ASSETS / "needs_A_1.png", 0.04, 0.42, 0.22, 0.46, "A-1 부담 최소")
    image_box(needs, ASSETS / "needs_A_2.png", 0.28, 0.42, 0.22, 0.46, "A-2 부담 최소")
    image_box(needs, ASSETS / "needs_B_1.png", 0.52, 0.42, 0.22, 0.46, "B-1 학습 몰입")
    image_box(needs, ASSETS / "needs_B_2.png", 0.76, 0.42, 0.20, 0.46, "B-2 학습 몰입")
    needs.text(0.04, 0.28, "비교군 A: 과제·팀플·시험 부담이 적고, 학점이 후하며 편한 분위기의 수업 선호", fontsize=10.5, color=NAVY, fontweight="bold")
    needs.text(0.04, 0.18, "비교군 B: 시험 중심, 난이도 있는 수업, 체계적인 강의 운영과 내용 중심 학습 선호", fontsize=10.5, color=NAVY, fontweight="bold")
    needs.text(0.04, 0.08, "통제 조건: 동일 전공 4과목 · 18학점 · 교양 추가 · 교양 키워드 없음 · 시간대/공강 상관없음", fontsize=10.2, color="#354D61")

    experiment = add_card(fig, x3, 0.695, w, 0.130, "COMPARISON EXPERIMENT")
    mini_metric(experiment, 0.04, 0.57, "비교군 A", "부담 최소형", "#BFEAF8")
    mini_metric(experiment, 0.36, 0.57, "비교군 B", "학습 몰입형", "#FFD4D0")
    mini_metric(experiment, 0.68, 0.57, "목표 학점", "18학점", "#FFE0A3")
    experiment.text(0.04, 0.35, "사용자 니즈만 다르게 설정하고 전공 과목, 목표 학점, 교양 조건은 동일하게 통제하였다.", fontsize=10.4, color="#354D61")
    experiment.text(0.04, 0.17, "비교 목적: 니즈 벡터 변화가 강의평 적합도와 추천 결과에 미치는 영향 확인", fontsize=10.4, color="#354D61", fontweight="bold")

    charts = add_card(fig, x3, 0.365, w, 0.315, "RESULTS")
    image_box(charts, VIS / "need_vector_radar.png", 0.03, 0.38, 0.45, 0.52, "니즈 벡터")
    image_box(charts, VIS / "result_score_bars.png", 0.52, 0.38, 0.45, 0.52, "추천 점수")
    mini_metric(charts, 0.05, 0.17, "비교군 A", "75.8점", "#BFEAF8")
    mini_metric(charts, 0.36, 0.17, "비교군 B", "80.0점", "#FFD4D0")
    mini_metric(charts, 0.67, 0.17, "탐색 조합", "34,154 / 32,559", "#C7EFEA")
    charts.text(0.05, 0.07, "비교군 B는 강의평 적합도 89.1점으로 학습 몰입형 선호와 더 높은 유사도를 보였다.", fontsize=10.2, color="#354D61")

    timetables = add_card(fig, x3, 0.035, w, 0.315, "TIMETABLE RESULTS")
    image_box(timetables, ASSETS / "result_A_1.png", 0.04, 0.36, 0.28, 0.53, "A 대표 시안")
    image_box(timetables, ASSETS / "result_B_1.png", 0.36, 0.36, 0.28, 0.53, "B 대표 시안")
    image_box(timetables, ASSETS / "result_A_2.png", 0.68, 0.63, 0.13, 0.25, "A-B")
    image_box(timetables, ASSETS / "result_A_3.png", 0.83, 0.63, 0.13, 0.25, "A-C")
    image_box(timetables, ASSETS / "result_B_2.png", 0.68, 0.36, 0.13, 0.25, "B-B")
    image_box(timetables, ASSETS / "result_B_3.png", 0.83, 0.36, 0.13, 0.25, "B-C")
    timetables.text(0.05, 0.22, "A/B/C 시안은 시간 충돌을 제거한 뒤 최종 적합도, 공강, 시간대 기준을 달리하여 제시된다.", fontsize=10.2, color="#354D61")
    timetables.text(0.05, 0.12, "조건에 맞는 다른 시안이 부족한 경우 유사한 시안을 억지로 생성하지 않고 안내하도록 설계하였다.", fontsize=10.2, color="#354D61")

    fig.text(0.035, 0.015, "SSU-TIME · Advanced AI Mathematics Project Poster · A1 Portrait", fontsize=10, color="#6A8294")

    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "ssu_time_a1_poster.pdf", facecolor=fig.get_facecolor())
    fig.savefig(OUT / "ssu_time_a1_poster.png", facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__ == "__main__":
    create_poster()
