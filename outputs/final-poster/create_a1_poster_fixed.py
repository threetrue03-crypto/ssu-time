from __future__ import annotations

from io import BytesIO
from pathlib import Path
import textwrap

import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont, ImageOps


BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "outputs" / "final-poster"
ASSETS = OUT / "assets"
VIS = BASE / "outputs" / "poster-visualizations"

W, H = 4209, 5960  # A1 portrait at 180 dpi.
MARGIN = 112
GUTTER = 58
COL_W = (W - (MARGIN * 2) - (GUTTER * 2)) // 3
X1 = MARGIN
X2 = X1 + COL_W + GUTTER
X3 = X2 + COL_W + GUTTER

NAVY = "#14324F"
SKY = "#DDF5FB"
CARD = "#FFFFFF"
INK = "#2F4658"
MUTED = "#667F91"
LINE = "#BFEAF8"
BLUE = "#35B6E8"
RED = "#FF8984"
MINT = "#BFEDE8"
YELLOW = "#FFE1A6"
PURPLE = "#D9CBFF"
PALE_BLUE = "#BFEAF8"

FONT_DIR = Path("C:/Windows/Fonts")
REGULAR = FONT_DIR / "malgun.ttf"
BOLD = FONT_DIR / "malgunbd.ttf"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = BOLD if bold and BOLD.exists() else REGULAR
    return ImageFont.truetype(str(path), size=size)


F = {
    "title": font(124, True),
    "subtitle": font(56, True),
    "meta": font(31),
    "section": font(39, True),
    "body": font(27),
    "body_bold": font(27, True),
    "small": font(23),
    "small_bold": font(23, True),
    "tiny": font(19),
    "tiny_bold": font(19, True),
    "metric": font(34, True),
    "flow": font(23, True),
}


def rounded(draw: ImageDraw.ImageDraw, box, radius=28, fill=CARD, outline=None, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text_size(draw: ImageDraw.ImageDraw, text: str, ft: ImageFont.FreeTypeFont):
    box = draw.textbbox((0, 0), text, font=ft)
    return box[2] - box[0], box[3] - box[1]


def wrap_line(draw: ImageDraw.ImageDraw, text: str, ft: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if text_size(draw, trial, ft)[0] <= max_w:
            current = trial
            continue
        if current:
            lines.append(current)
        current = word
        while text_size(draw, current, ft)[0] > max_w and len(current) > 1:
            part = ""
            for char in current:
                if text_size(draw, part + char, ft)[0] > max_w:
                    break
                part += char
            lines.append(part)
            current = current[len(part) :]
    if current:
        lines.append(current)
    return lines


def draw_wrapped(draw, xy, text, ft, fill=INK, max_w=500, line_h=None, spacing=1.0):
    x, y = xy
    line_h = line_h or int(ft.size * 1.45)
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            y += int(line_h * 0.55)
            continue
        for line in wrap_line(draw, paragraph, ft, max_w):
            draw.text((x, y), line, font=ft, fill=fill)
            y += int(line_h * spacing)
    return y


def card(img: Image.Image, x, y, w, h, title: str):
    d = ImageDraw.Draw(img)
    rounded(d, (x, y, x + w, y + h), 30, CARD)
    d.text((x + 38, y + 34), title, font=F["section"], fill=NAVY)
    return (x + 38, y + 95, w - 76, h - 125)


def paste_contain(base: Image.Image, path: Path, box, bg="#F7FCFF", outline=LINE):
    x, y, w, h = box
    d = ImageDraw.Draw(base)
    rounded(d, (x, y, x + w, y + h), 24, bg, outline, 2)
    im = Image.open(path).convert("RGBA")
    im = ImageOps.contain(im, (w - 18, h - 18), Image.Resampling.LANCZOS)
    px = x + (w - im.width) // 2
    py = y + (h - im.height) // 2
    base.alpha_composite(im, (px, py))


def paste_label_image(base: Image.Image, path: Path, box, label: str):
    x, y, w, h = box
    paste_contain(base, path, (x, y + 34, w, h - 34))
    d = ImageDraw.Draw(base)
    d.text((x + 8, y), label, font=F["tiny_bold"], fill=NAVY)


def metric(draw, x, y, w, label, value, fill):
    rounded(draw, (x, y, x + w, y + 116), 28, fill)
    draw.text((x + 26, y + 18), label, font=F["tiny_bold"], fill=NAVY)
    draw.text((x + 26, y + 62), value, font=F["metric"], fill=NAVY)


def formula_image(expr: str, width: int, height: int, fontsize=36):
    fig = plt.figure(figsize=(width / 180, height / 180), dpi=180)
    fig.patch.set_alpha(0)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.text(0.02, 0.55, expr, fontsize=fontsize, color=NAVY, va="center")
    buf = BytesIO()
    fig.savefig(buf, format="png", transparent=True, dpi=180)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGBA")


def flow_step(draw, x, y, w, h, label, fill):
    rounded(draw, (x, y, x + w, y + h), 26, fill)
    lines = textwrap.wrap(label, width=7)
    total = len(lines) * 28
    ty = y + (h - total) // 2
    for line in lines:
        tw, _ = text_size(draw, line, F["flow"])
        draw.text((x + (w - tw) // 2, ty), line, font=F["flow"], fill=NAVY)
        ty += 30


def arrow(draw, x1, y1, x2, y2):
    draw.line((x1, y1, x2, y2), fill="#75B9D0", width=5)
    draw.polygon([(x2, y2), (x2 - 18, y2 - 10), (x2 - 18, y2 + 10)], fill="#75B9D0")


def build():
    img = Image.new("RGBA", (W, H), SKY)
    d = ImageDraw.Draw(img)

    # Header
    d.text((MARGIN, 54), "SSU-TIME", font=F["title"], fill=NAVY)
    d.text((MARGIN, 220), "강의평 기반 맞춤형 시간표 추천 시스템", font=F["subtitle"], fill=NAVY)
    d.text(
        (MARGIN, 324),
        "사용자 니즈 벡터와 강의평 벡터의 유사도 분석을 활용한 2026학년도 1학기 시간표 자동 생성",
        font=F["meta"],
        fill=MUTED,
    )
    d.text((MARGIN, 415), "팀명: 너시간표내꺼   |   조세진 · 박시우 · 안민기 · 윤서준 · 이동연   |   AI소프트웨어학부", font=F["small"], fill=MUTED)
    d.text((MARGIN, 486), "고급AI수학 · 김창훈 교수님 · 2026.06.18", font=F["small"], fill=MUTED)
    d.text((W - 1150, 70), "너시간표내꺼", font=font(70, True), fill=NAVY)
    mascot = Image.open(ASSETS / "mascot_lab.png").convert("RGBA")
    mascot = ImageOps.contain(mascot, (360, 360), Image.Resampling.LANCZOS)
    img.alpha_composite(mascot, (W - 470, 86))

    y0 = 690
    gap = 52

    # Left column
    x, y = X1, y0
    ix, iy, iw, ih = card(img, x, y, COL_W, 620, "INTRODUCTION")
    draw_wrapped(
        d,
        (ix, iy + 10),
        "대학생이 시간표를 구성할 때는 단순한 시간 충돌뿐 아니라 교수자의 강의 방식, 과제·시험 부담, 출석 기준, 학점 부여 방식, 수업 분위기까지 함께 고려해야 한다.\n\nSSU-TIME은 과목 DB와 강의평 데이터를 결합하고 사용자의 선호를 수치화하여 맞춤형 시간표 시안을 자동으로 생성한다.",
        F["body"],
        max_w=iw,
        line_h=44,
    )

    y += 620 + gap
    ix, iy, iw, ih = card(img, x, y, COL_W, 770, "PROJECT GOALS")
    bullets = [
        ("과목·강의평 DB 결합", "수업 시간, 학점, 이수 구분, 교수자 정보를 강의평과 매칭한다."),
        ("사용자 니즈 벡터화", "질문지 응답을 과제량, 시험비중, 난이도 등 7차원 벡터로 변환한다."),
        ("맞춤형 시간표 생성", "벡터 유사도, 시간 충돌, 목표 학점을 함께 고려해 시안을 추천한다."),
    ]
    by = iy + 8
    for idx, (title, body) in enumerate(bullets):
        d.text((ix, by), "•", font=font(36, True), fill=[BLUE, RED, "#49C7BE"][idx])
        d.text((ix + 42, by + 5), title, font=F["body_bold"], fill=NAVY)
        by = draw_wrapped(d, (ix + 42, by + 52), body, F["body"], max_w=iw - 54, line_h=40) + 34

    y += 770 + gap
    ix, iy, iw, ih = card(img, x, y, COL_W, 610, "DATASET")
    metric(d, ix, iy + 14, 330, "과목 DB", "401개", PALE_BLUE)
    metric(d, ix + 370, iy + 14, 350, "교양 후보풀", "309개", MINT)
    metric(d, ix + 760, iy + 14, 360, "강의평 프로필", "225개", PURPLE)
    draw_wrapped(
        d,
        (ix, iy + 178),
        "주요 컬럼: 과목명, 교수명, 이수 구분, 학점, 수업 시간, 강의실, 강의평, 별점, 리뷰 수\n\n과목-교수 조합별 강의평을 분석하여 강의 특성 벡터를 생성하였다.",
        F["body"],
        max_w=iw,
        line_h=43,
    )

    y += 610 + gap
    ix, iy, iw, ih = card(img, x, y, COL_W, 1280, "LINEAR ALGEBRA MODEL")
    d.text((ix, iy + 10), "사용자 니즈 벡터와 강의평 벡터", font=F["body_bold"], fill=NAVY)
    img.alpha_composite(formula_image(r"$\mathbf{u}=(u_1,u_2,\ldots,u_7)$", 1120, 110, 35), (ix + 20, iy + 92))
    img.alpha_composite(formula_image(r"$\mathbf{l}=(l_1,l_2,\ldots,l_7)$", 1120, 110, 35), (ix + 20, iy + 225))
    draw_wrapped(d, (ix, iy + 380), "강의평 적합도는 벡터의 방향과 거리 정보를 함께 사용한다.", F["body"], max_w=iw)
    img.alpha_composite(formula_image(r"$\cos\theta=\frac{\mathbf{u}\cdot\mathbf{l}}{\|\mathbf{u}\|\,\|\mathbf{l}\|}$", 1080, 165, 39), (ix + 25, iy + 455))
    d.text((ix, iy + 700), "최종 추천 점수", font=F["body_bold"], fill=NAVY)
    img.alpha_composite(
        formula_image(
            r"$S(T)=0.32S_{review}+0.12S_{time}$",
            1150,
            90,
            27,
        ),
        (ix, iy + 770),
    )
    img.alpha_composite(
        formula_image(r"$+\,0.12S_{dayoff}+0.09S_{keyword}+0.35S_{credit}$", 1110, 90, 25),
        (ix, iy + 865),
    )
    draw_wrapped(
        d,
        (ix, iy + 1010),
        "두 벡터의 방향이 가까울수록 사용자의 선호와 강의 특성이 잘 맞는 것으로 판단한다.",
        F["small"],
        max_w=iw,
        line_h=35,
    )

    y += 1280 + gap
    ix, iy, iw, ih = card(img, x, y, COL_W, 1590, "CONCLUSION")
    draw_wrapped(
        d,
        (ix, iy + 10),
        "동일한 전공 과목과 목표 학점 조건에서도 사용자 니즈 벡터가 달라지면 강의평 벡터와의 유사도 계산 결과가 달라져 추천 시안이 변화하였다.\n\n이를 통해 선형대수 기반 벡터 유사도 계산이 개인화된 시간표 추천 시스템에 활용될 수 있음을 확인하였다.\n\n향후 더 많은 강의평 데이터와 실제 사용자 피드백을 반영하여 추천 정확도를 개선할 수 있다.",
        F["body"],
        max_w=iw,
        line_h=43,
    )

    # Middle column
    x, y = X2, y0
    ix, iy, iw, ih = card(img, x, y, COL_W, 620, "SYSTEM PIPELINE")
    flow_step(d, ix, iy + 70, 185, 110, "과목 DB", PALE_BLUE)
    flow_step(d, ix, iy + 260, 185, 110, "강의평 DB", PURPLE)
    flow_step(d, ix + 305, iy + 165, 220, 130, "벡터화", MINT)
    flow_step(d, ix + 620, iy + 165, 220, 130, "유사도 계산", YELLOW)
    flow_step(d, ix + 930, iy + 165, 190, 130, "A/B/C 시안", "#FFD4D0")
    arrow(d, ix + 185, iy + 125, ix + 305, iy + 220)
    arrow(d, ix + 185, iy + 315, ix + 305, iy + 240)
    arrow(d, ix + 525, iy + 230, ix + 620, iy + 230)
    arrow(d, ix + 840, iy + 230, ix + 930, iy + 230)

    y += 620 + gap
    ix, iy, iw, ih = card(img, x, y, COL_W, 1650, "WEB APP FLOW")
    flow_imgs = [
        ("첫 화면", "home.png"),
        ("과목 선택", "course_select.png"),
        ("니즈 입력", "needs_A_1.png"),
        ("로딩", "loading.png"),
        ("결과", "result_A_1.png"),
    ]
    box_w = (iw - 4 * 18) // 5
    for idx, (label, filename) in enumerate(flow_imgs):
        paste_label_image(img, ASSETS / filename, (ix + idx * (box_w + 18), iy + 20, box_w, 980), label)
    draw_wrapped(
        d,
        (ix, iy + 1100),
        "사용자는 전공 과목을 직접 선택하고, 목표 학점과 수업 선호를 질문지로 입력한다.\n\n백엔드는 강의평 벡터와 사용자 니즈 벡터를 비교하여 시간 충돌이 없는 시간표 조합을 생성한다.\n\n최종적으로 적합도 높은 시간표 시안을 A/B/C로 제시하고 추천 근거를 함께 제공한다.",
        F["body"],
        max_w=iw,
        line_h=43,
    )

    y += 1650 + gap
    ix, iy, iw, ih = card(img, x, y, COL_W, 2500, "QUESTIONNAIRE SETTINGS")
    q_imgs = [
        ("A-1 부담 최소", "needs_A_1.png"),
        ("A-2 부담 최소", "needs_A_2.png"),
        ("B-1 학습 몰입", "needs_B_1.png"),
        ("B-2 학습 몰입", "needs_B_2.png"),
    ]
    q_w = (iw - 3 * 22) // 4
    for idx, (label, filename) in enumerate(q_imgs):
        paste_label_image(img, ASSETS / filename, (ix + idx * (q_w + 22), iy + 20, q_w, 1280), label)
    draw_wrapped(
        d,
        (ix, iy + 1420),
        "비교군 A: 과제·팀플·시험 부담이 적고, 학점이 후하며 편한 분위기의 수업 선호\n\n비교군 B: 시험 중심, 난이도 있는 수업, 체계적인 강의 운영과 내용 중심 학습 선호\n\n통제 조건: 동일 전공 4과목 · 18학점 · 교양 추가 · 교양 키워드 없음 · 시간대/공강 상관없음",
        F["body_bold"],
        max_w=iw,
        line_h=47,
    )

    # Right column
    x, y = X3, y0
    ix, iy, iw, ih = card(img, x, y, COL_W, 620, "COMPARISON EXPERIMENT")
    metric(d, ix, iy + 40, 330, "비교군 A", "부담 최소형", PALE_BLUE)
    metric(d, ix + 375, iy + 40, 330, "비교군 B", "학습 몰입형", "#FFD4D0")
    metric(d, ix + 750, iy + 40, 330, "목표 학점", "18학점", YELLOW)
    draw_wrapped(
        d,
        (ix, iy + 205),
        "사용자 니즈만 다르게 설정하고 전공 과목, 목표 학점, 교양 조건은 동일하게 통제하였다.\n\n비교 목적: 니즈 벡터 변화가 강의평 적합도와 추천 결과에 미치는 영향 확인",
        F["body"],
        max_w=iw,
        line_h=43,
    )

    y += 620 + gap
    ix, iy, iw, ih = card(img, x, y, COL_W, 1640, "RESULTS")
    paste_label_image(img, VIS / "need_vector_radar.png", (ix, iy + 15, 535, 720), "니즈 벡터")
    paste_label_image(img, VIS / "result_score_bars.png", (ix + 585, iy + 15, 535, 720), "추천 점수")
    metric(d, ix + 20, iy + 820, 315, "비교군 A", "75.8점", PALE_BLUE)
    metric(d, ix + 390, iy + 820, 315, "비교군 B", "80.0점", "#FFD4D0")
    metric(d, ix + 760, iy + 820, 330, "탐색 조합", "34,154 / 32,559", MINT)
    draw_wrapped(
        d,
        (ix, iy + 1045),
        "비교군 B는 강의평 적합도 89.1점으로 학습 몰입형 선호와 더 높은 유사도를 보였다.\n\n같은 전공·학점 조건에서도 사용자 니즈 벡터가 달라지면 강의평 벡터와의 유사도 계산 결과가 달라져 추천 시안이 달라진다.",
        F["body_bold"],
        max_w=iw,
        line_h=46,
    )

    y += 1640 + gap
    ix, iy, iw, ih = card(img, x, y, COL_W, 2700, "TIMETABLE RESULTS")
    paste_label_image(img, ASSETS / "result_A_1.png", (ix, iy + 15, 370, 1320), "A 대표 시안")
    paste_label_image(img, ASSETS / "result_B_1.png", (ix + 410, iy + 15, 370, 1320), "B 대표 시안")
    paste_label_image(img, ASSETS / "result_A_2.png", (ix + 820, iy + 15, 150, 630), "A-B")
    paste_label_image(img, ASSETS / "result_A_3.png", (ix + 990, iy + 15, 150, 630), "A-C")
    paste_label_image(img, ASSETS / "result_B_2.png", (ix + 820, iy + 705, 150, 630), "B-B")
    paste_label_image(img, ASSETS / "result_B_3.png", (ix + 990, iy + 705, 150, 630), "B-C")
    draw_wrapped(
        d,
        (ix, iy + 1485),
        "A/B/C 시안은 시간 충돌을 제거한 뒤 최종 적합도, 공강, 시간대 기준을 달리하여 제시된다.\n\n조건에 맞는 다른 시안이 부족한 경우 유사한 시안을 억지로 생성하지 않고 안내하도록 설계하였다.",
        F["body"],
        max_w=iw,
        line_h=43,
    )

    d.text((MARGIN, H - 58), "SSU-TIME · Advanced AI Mathematics Project Poster · A1 Portrait", font=F["tiny"], fill="#6A8294")

    OUT.mkdir(parents=True, exist_ok=True)
    rgb = Image.new("RGB", img.size, SKY)
    rgb.paste(img, mask=img.split()[-1])
    rgb.save(OUT / "ssu_time_a1_poster_fixed.png", "PNG", dpi=(180, 180))
    rgb.save(OUT / "ssu_time_a1_poster_fixed.pdf", "PDF", resolution=180)
    # Also overwrite the default export names with the fixed version.
    rgb.save(OUT / "ssu_time_a1_poster.png", "PNG", dpi=(180, 180))
    rgb.save(OUT / "ssu_time_a1_poster.pdf", "PDF", resolution=180)


if __name__ == "__main__":
    build()
