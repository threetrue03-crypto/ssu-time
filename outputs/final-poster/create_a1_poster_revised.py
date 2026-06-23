from __future__ import annotations

from math import cos, pi, sin
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from reportlab.lib import colors
from reportlab.lib.pagesizes import A1
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "outputs" / "final-poster"
ASSETS = OUT / "assets"
PDF_OUT = OUT / "poster_a1_revised.pdf"
PNG_OUT = OUT / "poster_a1_revised.png"

PAGE_W, PAGE_H = A1  # 594mm x 841mm, portrait.
MARGIN = 44
GUTTER = 24
HEADER_H = 260
COL_W = (PAGE_W - MARGIN * 2 - GUTTER * 2) / 3
X = [MARGIN, MARGIN + COL_W + GUTTER, MARGIN + (COL_W + GUTTER) * 2]

NAVY = colors.HexColor("#14324F")
INK = colors.HexColor("#2E465B")
MUTED = colors.HexColor("#6B8292")
SKY_BG = colors.HexColor("#DDF5FB")
CARD = colors.white
LINE = colors.HexColor("#BFEAF8")
BLUE = colors.HexColor("#2FAFE5")
BLUE_SOFT = colors.HexColor("#BDEBFB")
MINT = colors.HexColor("#BEEBE6")
YELLOW = colors.HexColor("#FFE1A6")
PINK = colors.HexColor("#FFD1CD")
PURPLE = colors.HexColor("#D9CBFF")
PALE = colors.HexColor("#F7FCFF")


def setup_fonts() -> None:
    font_dir = Path("C:/Windows/Fonts")
    pdfmetrics.registerFont(TTFont("Malgun", str(font_dir / "malgun.ttf")))
    pdfmetrics.registerFont(TTFont("Malgun-Bold", str(font_dir / "malgunbd.ttf")))


def draw_text(c: canvas.Canvas, x: float, y: float, text: str, size: float, color=INK, bold=False) -> None:
    c.setFillColor(color)
    c.setFont("Malgun-Bold" if bold else "Malgun", size)
    c.drawString(x, y, text)


def text_width(text: str, size: float, bold=False) -> float:
    return pdfmetrics.stringWidth(text, "Malgun-Bold" if bold else "Malgun", size)


def wrap_text(text: str, size: float, max_w: float, bold=False) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue
        current = ""
        for word in paragraph.split(" "):
            trial = word if not current else f"{current} {word}"
            if text_width(trial, size, bold) <= max_w:
                current = trial
                continue
            if current:
                lines.append(current)
            current = word
            while text_width(current, size, bold) > max_w and len(current) > 1:
                part = ""
                for ch in current:
                    if text_width(part + ch, size, bold) > max_w:
                        break
                    part += ch
                lines.append(part)
                current = current[len(part) :]
        if current:
            lines.append(current)
    return lines


def paragraph(c: canvas.Canvas, x: float, y: float, text: str, size: float = 18, max_w: float = 300, line_h: float | None = None, color=INK, bold=False) -> float:
    line_h = line_h or size * 1.38
    c.setFillColor(color)
    c.setFont("Malgun-Bold" if bold else "Malgun", size)
    for line in wrap_text(text, size, max_w, bold):
        if line:
            c.drawString(x, y, line)
        y -= line_h
    return y


def round_rect(c: canvas.Canvas, x: float, y: float, w: float, h: float, r: float, fill, stroke=None, sw: float = 1) -> None:
    c.setFillColor(fill)
    c.setStrokeColor(stroke or fill)
    c.setLineWidth(sw)
    c.roundRect(x, y, w, h, r, stroke=1 if stroke else 0, fill=1)


def top_to_y(top: float, h: float) -> float:
    return PAGE_H - top - h


def card(c: canvas.Canvas, x: float, top: float, w: float, h: float, title: str) -> tuple[float, float, float, float]:
    y = top_to_y(top, h)
    round_rect(c, x, y, w, h, 18, CARD)
    draw_text(c, x + 18, y + h - 34, title, 22, NAVY, True)
    c.setStrokeColor(colors.HexColor("#E2F5FB"))
    c.setLineWidth(1)
    c.line(x + 18, y + h - 48, x + w - 18, y + h - 48)
    return x + 18, y + 20, w - 36, h - 74


def bullet(c: canvas.Canvas, x: float, y: float, title: str, body: str, color, max_w: float) -> float:
    c.setFillColor(color)
    c.circle(x + 5, y + 7, 4, fill=1, stroke=0)
    draw_text(c, x + 20, y, title, 18, NAVY, True)
    return paragraph(c, x + 20, y - 27, body, 16.5, max_w - 20, 23, MUTED) - 10


def metric(c: canvas.Canvas, x: float, y: float, w: float, label: str, value: str, fill) -> None:
    round_rect(c, x, y, w, 78, 14, fill)
    draw_text(c, x + 14, y + 50, label, 14, NAVY, True)
    draw_text(c, x + 14, y + 18, value, 26, NAVY, True)


def image_fit(c: canvas.Canvas, path: Path, x: float, y: float, w: float, h: float, bg=PALE, stroke=LINE, radius=16) -> None:
    round_rect(c, x, y, w, h, radius, bg, stroke, 1)
    with Image.open(path) as im:
        iw, ih = im.size
    scale = min((w - 10) / iw, (h - 10) / ih)
    dw, dh = iw * scale, ih * scale
    c.drawImage(ImageReader(str(path)), x + (w - dw) / 2, y + (h - dh) / 2, dw, dh, mask="auto")


def pill(c: canvas.Canvas, x: float, y: float, text: str, fill, color=NAVY, size=15, bold=True) -> None:
    w = text_width(text, size, bold) + 24
    round_rect(c, x, y, w, 32, 16, fill)
    draw_text(c, x + 12, y + 9, text, size, color, bold)


def pipeline(c: canvas.Canvas, x: float, y: float, w: float) -> None:
    labels = [
        ("과목 DB", BLUE_SOFT),
        ("강의평 DB", PURPLE),
        ("벡터화", MINT),
        ("유사도 계산", YELLOW),
        ("A/B/C 시안", PINK),
    ]
    boxes = [
        (x, y + 76, 98, 54),
        (x, y, 98, 54),
        (x + 160, y + 38, 122, 60),
        (x + 338, y + 38, 132, 60),
        (x + 530, y + 38, 120, 60),
    ]
    for (label, fill), (bx, by, bw, bh) in zip(labels, boxes):
        round_rect(c, bx, by, bw, bh, 12, fill)
        draw_text(c, bx + (bw - text_width(label, 15, True)) / 2, by + 20, label, 15, NAVY, True)
    c.setStrokeColor(colors.HexColor("#73BCD2"))
    c.setLineWidth(3)
    for sx, sy, ex, ey in [
        (x + 98, y + 103, x + 160, y + 72),
        (x + 98, y + 27, x + 160, y + 62),
        (x + 282, y + 68, x + 338, y + 68),
        (x + 470, y + 68, x + 530, y + 68),
    ]:
        c.line(sx, sy, ex, ey)
        c.setFillColor(colors.HexColor("#73BCD2"))
        c.circle(ex, ey, 3.5, fill=1, stroke=0)


def radar_chart(c: canvas.Canvas, cx: float, cy: float, r: float) -> None:
    labels = ["과제량", "팀플", "시험", "난이도", "학점", "출석", "분위기"]
    a = [0.10, 0.10, 0.10, 0.15, 0.90, 0.10, 0.92]
    b = [0.85, 0.85, 0.85, 0.82, 0.45, 0.75, 0.45]
    n = len(labels)
    c.setStrokeColor(colors.HexColor("#D5ECF5"))
    c.setLineWidth(1)
    for frac in [0.25, 0.5, 0.75, 1.0]:
        pts = []
        for i in range(n):
            ang = pi / 2 - 2 * pi * i / n
            pts.append((cx + r * frac * cos(ang), cy + r * frac * sin(ang)))
        c.lines([(pts[i][0], pts[i][1], pts[(i + 1) % n][0], pts[(i + 1) % n][1]) for i in range(n)])
    for i, label in enumerate(labels):
        ang = pi / 2 - 2 * pi * i / n
        x = cx + (r + 25) * cos(ang)
        y = cy + (r + 25) * sin(ang)
        draw_text(c, x - text_width(label, 11, True) / 2, y - 4, label, 11, NAVY, True)

    def polygon(values: list[float], stroke, fill):
        pts = []
        for i, value in enumerate(values):
            ang = pi / 2 - 2 * pi * i / n
            pts.append((cx + r * value * cos(ang), cy + r * value * sin(ang)))
        path = c.beginPath()
        path.moveTo(*pts[0])
        for p in pts[1:]:
            path.lineTo(*p)
        path.close()
        c.setFillColor(fill)
        c.setStrokeColor(stroke)
        c.setLineWidth(2.5)
        c.drawPath(path, stroke=1, fill=1)

    polygon(a, BLUE, colors.Color(0.18, 0.69, 0.90, alpha=0.15))
    polygon(b, colors.HexColor("#FF8A82"), colors.Color(1.0, 0.54, 0.50, alpha=0.16))


def bar_chart(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    groups = [("최종", 75.8, 80.0), ("강의평", 76.0, 81.3), ("교양", 34.0, 32.5)]
    c.setStrokeColor(colors.HexColor("#DDF1F8"))
    c.setLineWidth(1)
    for i in range(5):
        yy = y + i * h / 4
        c.line(x, yy, x + w, yy)
        draw_text(c, x - 30, yy - 4, str(i * 25), 9, MUTED)
    gap = w / len(groups)
    bw = 26
    for idx, (label, av, bv) in enumerate(groups):
        gx = x + gap * idx + gap / 2
        ah = h * av / 100
        bh = h * bv / 100
        c.setFillColor(BLUE)
        c.rect(gx - bw - 3, y, bw, ah, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#FF8A82"))
        c.rect(gx + 3, y, bw, bh, fill=1, stroke=0)
        draw_text(c, gx - 35, y - 25, label, 12, NAVY, True)
        draw_text(c, gx - bw - 4, y + ah + 8, f"{av:.0f}", 10, NAVY, True)
        draw_text(c, gx + 1, y + bh + 8, f"{bv:.0f}", 10, NAVY, True)
    pill(c, x + 8, y + h + 20, "A", BLUE_SOFT, size=11)
    pill(c, x + 58, y + h + 20, "B", PINK, size=11)


def draw_background(c: canvas.Canvas) -> None:
    c.setFillColor(SKY_BG)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setStrokeColor(colors.Color(0.18, 0.69, 0.90, alpha=0.12))
    c.setLineWidth(0.5)
    step = 34
    x = 0
    while x <= PAGE_W:
        c.line(x, 0, x, PAGE_H)
        x += step
    y = 0
    while y <= PAGE_H:
        c.line(0, y, PAGE_W, y)
        y += step


def draw_pdf() -> None:
    setup_fonts()
    c = canvas.Canvas(str(PDF_OUT), pagesize=A1)
    draw_background(c)

    # Header
    draw_text(c, MARGIN, PAGE_H - 78, "SSU-TIME", 82, NAVY, True)
    draw_text(c, MARGIN, PAGE_H - 150, "강의평 기반 맞춤형 시간표 추천 시스템", 31, NAVY, True)
    paragraph(
        c,
        MARGIN,
        PAGE_H - 190,
        "사용자 니즈 벡터와 강의평 벡터의 유사도 분석으로 2026학년도 1학기 시간표를 자동 추천",
        17,
        880,
        23,
        MUTED,
    )
    draw_text(c, MARGIN, PAGE_H - 230, "팀 너시간표내꺼  |  조세진 · 박시우 · 안민기 · 윤서준 · 이동연  |  AI소프트웨어학부", 15, MUTED)
    draw_text(c, MARGIN, PAGE_H - 254, "고급AI수학 · 김창훈 교수님 · 2026.06.18", 15, MUTED)
    draw_text(c, PAGE_W - 405, PAGE_H - 78, "너시간표내꺼", 33, NAVY, True)
    c.drawImage(ImageReader(str(ASSETS / "qr_code.png")), PAGE_W - 405, PAGE_H - 250, 138, 138, mask="auto")
    c.drawImage(ImageReader(str(ASSETS / "mascot_lab.png")), PAGE_W - 225, PAGE_H - 250, 138, 138, mask="auto")

    top = HEADER_H + 20

    # Left column
    ix, iy, iw, ih = card(c, X[0], top, COL_W, 370, "PROBLEM & GOALS")
    y = iy + ih - 26
    y = bullet(c, ix, y, "문제", "시간 충돌, 교수별 강의 방식, 과제·시험 부담을 한 번에 비교하기 어렵다.", BLUE, iw)
    y = bullet(c, ix, y, "목표", "과목 DB와 강의평 DB를 결합해 개인 선호에 맞는 A/B/C 시안을 생성한다.", MINT, iw)
    y = bullet(c, ix, y, "핵심", "선호도 입력 → 강의 벡터 비교 → 시간표 추천", YELLOW, iw)

    ix, iy, iw, ih = card(c, X[0], top + 394, COL_W, 300, "DATASET")
    metric(c, ix, iy + ih - 95, 138, "과목 DB", "401개", BLUE_SOFT)
    metric(c, ix + 154, iy + ih - 95, 138, "교양 후보", "309개", MINT)
    metric(c, ix + 308, iy + ih - 95, 138, "강의평 프로필", "225개", PURPLE)
    paragraph(c, ix, iy + ih - 130, "과목명, 교수명, 학점, 시간, 이수구분, 강의평, 별점, 리뷰 수를 정제했다.", 17, iw, 24, INK)
    paragraph(c, ix, iy + ih - 190, "과목-교수 조합별로 리뷰를 묶어 강의 특성 벡터를 생성했다.", 17, iw, 24, INK)

    ix, iy, iw, ih = card(c, X[0], top + 718, COL_W, 590, "LINEAR ALGEBRA MODEL")
    y = iy + ih - 20
    draw_text(c, ix, y, "사용자 니즈 벡터와 강의평 벡터", 18, NAVY, True)
    y -= 58
    draw_text(c, ix + 12, y, "u = (u_1, u_2, ..., u_7)", 38, NAVY, True)
    y -= 56
    draw_text(c, ix + 12, y, "l = (l_1, l_2, ..., l_7)", 38, NAVY, True)
    y -= 55
    paragraph(c, ix, y, "두 벡터의 방향이 가까울수록 사용자 선호와 강의 특성이 잘 맞는 것으로 판단한다.", 17, iw, 24, INK)
    y -= 92
    draw_text(c, ix, y, "코사인 유사도", 18, NAVY, True)
    y -= 62
    draw_text(c, ix + 12, y, "cos θ = (u · l) / (||u|| ||l||)", 34, NAVY, True)
    y -= 72
    draw_text(c, ix, y, "최종 추천 점수", 18, NAVY, True)
    y -= 45
    draw_text(c, ix + 12, y, "S(T) = 0.32Sreview + 0.12Stime", 23, NAVY, True)
    y -= 36
    draw_text(c, ix + 12, y, "+ 0.12Sdayoff + 0.09Skeyword + 0.35Scredit", 23, NAVY, True)

    ix, iy, iw, ih = card(c, X[0], top + 1332, COL_W, 335, "CONCLUSION")
    y = iy + ih - 26
    y = bullet(c, ix, y, "개인화", "같은 과목 조건에서도 니즈 벡터에 따라 다른 시안이 생성된다.", BLUE, iw)
    y = bullet(c, ix, y, "설명 가능성", "강의평·시간대·공강·학점 기준을 추천 근거로 제시한다.", MINT, iw)
    bullet(c, ix, y, "확장성", "더 많은 강의평과 사용자 피드백을 반영해 추천 정확도를 높일 수 있다.", YELLOW, iw)

    # Center column
    ix, iy, iw, ih = card(c, X[1], top, COL_W, 330, "SYSTEM PIPELINE")
    pipeline(c, ix + 8, iy + ih - 145, iw - 16)
    paragraph(c, ix, iy + ih - 198, "과목 DB와 강의평 DB를 벡터로 변환하고, 유사도와 시간표 제약을 함께 계산한다.", 18, iw, 25, INK)

    ix, iy, iw, ih = card(c, X[1], top + 354, COL_W, 690, "WEB APP FLOW")
    shot_w = (iw - 28) / 3
    shot_h = 470
    labels = [("1 과목 선택", "course_select.png"), ("2 니즈 입력", "needs_A_1.png"), ("3 시안 확인", "result_A_1.png")]
    for i, (label, img_name) in enumerate(labels):
        x0 = ix + i * (shot_w + 14)
        draw_text(c, x0, iy + ih - 24, label, 15, NAVY, True)
        image_fit(c, ASSETS / img_name, x0, iy + ih - 48 - shot_h, shot_w, shot_h)
    paragraph(c, ix, iy + 22, "전공 과목을 선택하고 기본 정보·개인 니즈를 입력하면 추천 시간표와 추천 근거를 확인한다.", 18, iw, 25, INK)

    ix, iy, iw, ih = card(c, X[1], top + 1068, COL_W, 600, "QUESTIONNAIRE SETTINGS")
    half = (iw - 16) / 2
    round_rect(c, ix, iy + ih - 158, half, 118, 16, BLUE_SOFT)
    draw_text(c, ix + 16, iy + ih - 74, "비교군 A", 15, NAVY, True)
    draw_text(c, ix + 16, iy + ih - 108, "부담 최소형", 27, NAVY, True)
    paragraph(c, ix + 16, iy + ih - 136, "과제 적게 · 팀플 회피 · 학점 중시", 15, half - 30, 20, INK)
    round_rect(c, ix + half + 16, iy + ih - 158, half, 118, 16, PINK)
    draw_text(c, ix + half + 32, iy + ih - 74, "비교군 B", 15, NAVY, True)
    draw_text(c, ix + half + 32, iy + ih - 108, "학습 몰입형", 27, NAVY, True)
    paragraph(c, ix + half + 32, iy + ih - 136, "과제 허용 · 팀플 선호 · 내용 중시", 15, half - 30, 20, INK)
    image_fit(c, ASSETS / "needs_A_2.png", ix + 12, iy + 36, half - 8, 330)
    image_fit(c, ASSETS / "needs_B_2.png", ix + half + 24, iy + 36, half - 8, 330)

    # Right column
    ix, iy, iw, ih = card(c, X[2], top, COL_W, 790, "RESULTS")
    metric(c, ix, iy + ih - 96, 130, "비교군 A", "75.8점", BLUE_SOFT)
    metric(c, ix + 148, iy + ih - 96, 130, "비교군 B", "80.0점", PINK)
    metric(c, ix + 296, iy + ih - 96, 150, "탐색 조합", "34,154+", MINT)
    draw_text(c, ix, iy + ih - 142, "니즈 벡터 비교", 16, NAVY, True)
    radar_chart(c, ix + 142, iy + ih - 318, 104)
    draw_text(c, ix + 246, iy + ih - 142, "추천 점수 비교", 16, NAVY, True)
    bar_chart(c, ix + 258, iy + ih - 386, 178, 185)
    paragraph(c, ix, iy + 98, "결론: 같은 전공 4과목·18학점 조건에서도 사용자 니즈에 따라 추천 시안이 달라졌다.", 20, iw, 28, NAVY, True)
    paragraph(c, ix, iy + 40, "B 조건은 학습 몰입 선호가 강의평 벡터와 더 높게 맞아 종합 점수가 상승했다.", 17, iw, 24, INK)

    ix, iy, iw, ih = card(c, X[2], top + 814, COL_W, 830, "TIMETABLE RESULTS")
    half = (iw - 18) / 2
    draw_text(c, ix, iy + ih - 26, "A 대표 시안", 16, NAVY, True)
    draw_text(c, ix + half + 18, iy + ih - 26, "B 대표 시안", 16, NAVY, True)
    image_fit(c, ASSETS / "result_A_1.png", ix, iy + 82, half, 630)
    image_fit(c, ASSETS / "result_B_1.png", ix + half + 18, iy + 82, half, 630)
    paragraph(c, ix, iy + 32, "A/B/C 시안 중 대표 결과를 크게 배치해 추천 결과와 시간 분포를 한눈에 비교한다.", 17, iw, 24, INK)

    ix, iy, iw, ih = card(c, X[2], top + 1668, COL_W, 230, "POSTER TAKEAWAY")
    paragraph(c, ix, iy + ih - 25, "SSU-TIME은 강의평 문장을 수치 벡터로 바꾸고, 선형대수의 내적·노름·코사인 유사도로 사용자 선호와 강의 특성의 일치도를 계산한다.", 19, iw, 27, NAVY, True)
    paragraph(c, ix, iy + ih - 112, "계산 결과는 추천 점수와 시간표 시안으로 연결되어 사용자가 바로 비교할 수 있다.", 18, iw, 25, INK)

    draw_text(c, MARGIN, 28, "SSU-TIME · Advanced AI Mathematics Project Poster · A1 Portrait", 9, MUTED)
    c.save()


def make_preview() -> None:
    try:
        from pdf2image import convert_from_path

        pages = convert_from_path(str(PDF_OUT), dpi=120, first_page=1, last_page=1)
        pages[0].save(PNG_OUT)
    except Exception:
        make_preview_fallback()


def pil_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    font_dir = Path("C:/Windows/Fonts")
    return ImageFont.truetype(str(font_dir / ("malgunbd.ttf" if bold else "malgun.ttf")), size)


def pil_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, size: int, fill: str = "#2E465B", bold: bool = False) -> None:
    draw.text(xy, text, font=pil_font(size, bold), fill=fill)


def pil_wrap(draw: ImageDraw.ImageDraw, text: str, size: int, width: int, bold: bool = False) -> list[str]:
    font_obj = pil_font(size, bold)
    lines: list[str] = []
    for paragraph_text in text.split("\n"):
        current = ""
        for word in paragraph_text.split(" "):
            trial = word if not current else f"{current} {word}"
            if draw.textlength(trial, font=font_obj) <= width:
                current = trial
                continue
            if current:
                lines.append(current)
            current = word
        if current:
            lines.append(current)
    return lines


def pil_para(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, size: int, width: int, fill: str = "#2E465B", bold: bool = False, line_h: int | None = None) -> int:
    line_h = line_h or int(size * 1.45)
    for line in pil_wrap(draw, text, size, width, bold):
        pil_text(draw, (x, y), line, size, fill, bold)
        y += line_h
    return y


def pil_card(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, title: str) -> tuple[int, int, int, int]:
    draw.rounded_rectangle((x, y, x + w, y + h), radius=17, fill="#FFFFFF")
    pil_text(draw, (x + 16, y + 16), title, 20, "#14324F", True)
    draw.line((x + 16, y + 48, x + w - 16, y + 48), fill="#E2F5FB", width=1)
    return x + 16, y + 62, w - 32, h - 78


def pil_image_fit(base: Image.Image, path: Path, box: tuple[int, int, int, int]) -> None:
    x, y, w, h = box
    draw = ImageDraw.Draw(base)
    draw.rounded_rectangle((x, y, x + w, y + h), radius=15, fill="#F7FCFF", outline="#BFEAF8", width=1)
    im = Image.open(path).convert("RGBA")
    im = ImageOps.contain(im, (w - 8, h - 8), Image.Resampling.LANCZOS)
    base.alpha_composite(im, (x + (w - im.width) // 2, y + (h - im.height) // 2))


def pil_metric(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, label: str, value: str, fill: str) -> None:
    draw.rounded_rectangle((x, y, x + w, y + 66), radius=13, fill=fill)
    pil_text(draw, (x + 12, y + 11), label, 12, "#14324F", True)
    pil_text(draw, (x + 12, y + 34), value, 23, "#14324F", True)


def make_preview_fallback() -> None:
    w, h = 1404, 1986
    img = Image.new("RGBA", (w, h), "#DDF5FB")
    draw = ImageDraw.Draw(img)
    for x in range(0, w, 28):
        draw.line((x, 0, x, h), fill="#CDEFF8", width=1)
    for y in range(0, h, 28):
        draw.line((0, y, w, y), fill="#CDEFF8", width=1)

    margin, gutter, header = 37, 20, 234
    col_w = int((w - margin * 2 - gutter * 2) / 3)
    xs = [margin, margin + col_w + gutter, margin + (col_w + gutter) * 2]

    pil_text(draw, (margin, 31), "SSU-TIME", 70, "#14324F", True)
    pil_text(draw, (margin, 122), "강의평 기반 맞춤형 시간표 추천 시스템", 28, "#14324F", True)
    pil_para(draw, margin, 160, "사용자 니즈 벡터와 강의평 벡터의 유사도 분석으로 2026학년도 1학기 시간표를 자동 추천", 16, 820, "#6B8292")
    pil_text(draw, (margin, 202), "팀 너시간표내꺼  |  조세진 · 박시우 · 안민기 · 윤서준 · 이동연  |  AI소프트웨어학부", 13, "#6B8292")
    pil_text(draw, (w - 350, 42), "너시간표내꺼", 29, "#14324F", True)
    qr = Image.open(ASSETS / "qr_code.png").convert("RGBA")
    qr = ImageOps.contain(qr, (116, 116), Image.Resampling.LANCZOS)
    img.alpha_composite(qr, (w - 350, 92))
    mascot = Image.open(ASSETS / "mascot_lab.png").convert("RGBA")
    mascot = ImageOps.contain(mascot, (116, 116), Image.Resampling.LANCZOS)
    img.alpha_composite(mascot, (w - 190, 92))

    y0 = header
    ix, iy, iw, ih = pil_card(draw, xs[0], y0, col_w, 310, "PROBLEM & GOALS")
    yy = pil_para(draw, ix, iy, "문제  시간 충돌, 교수별 강의 방식, 과제·시험 부담을 한 번에 비교하기 어렵다.", 17, iw, "#2E465B", True)
    yy = pil_para(draw, ix, yy + 16, "목표  과목 DB와 강의평 DB를 결합해 개인 선호에 맞는 A/B/C 시안을 생성한다.", 17, iw, "#2E465B", True)
    pil_para(draw, ix, yy + 16, "핵심  선호도 입력 → 강의 벡터 비교 → 시간표 추천", 17, iw, "#2E465B", True)

    ix, iy, iw, ih = pil_card(draw, xs[0], y0 + 330, col_w, 252, "DATASET")
    mw = int((iw - 24) / 3)
    pil_metric(draw, ix, iy, mw, "과목 DB", "401개", "#BDEBFB")
    pil_metric(draw, ix + mw + 12, iy, mw, "교양 후보", "309개", "#BEEBE6")
    pil_metric(draw, ix + (mw + 12) * 2, iy, mw, "강의평", "225개", "#D9CBFF")
    pil_para(draw, ix, iy + 92, "과목명, 교수명, 학점, 시간, 이수구분, 강의평, 별점, 리뷰 수를 정제했다.", 16, iw)
    pil_para(draw, ix, iy + 148, "과목-교수 조합별로 리뷰를 묶어 강의 특성 벡터를 생성했다.", 16, iw)

    ix, iy, iw, ih = pil_card(draw, xs[0], y0 + 602, col_w, 492, "LINEAR ALGEBRA MODEL")
    pil_text(draw, (ix, iy), "사용자 니즈 벡터와 강의평 벡터", 17, "#14324F", True)
    pil_text(draw, (ix + 10, iy + 54), "u = (u_1, u_2, ..., u_7)", 30, "#14324F", True)
    pil_text(draw, (ix + 10, iy + 104), "l = (l_1, l_2, ..., l_7)", 30, "#14324F", True)
    pil_para(draw, ix, iy + 164, "두 벡터의 방향이 가까울수록 사용자 선호와 강의 특성이 잘 맞는 것으로 판단한다.", 16, iw)
    pil_text(draw, (ix, iy + 240), "cos θ = (u · l) / (||u|| ||l||)", 26, "#14324F", True)
    pil_text(draw, (ix, iy + 318), "S(T) = 0.32Sreview + 0.12Stime", 20, "#14324F", True)
    pil_text(draw, (ix, iy + 354), "+ 0.12Sdayoff + 0.09Skeyword + 0.35Scredit", 20, "#14324F", True)

    ix, iy, iw, ih = pil_card(draw, xs[0], y0 + 1114, col_w, 280, "CONCLUSION")
    pil_para(draw, ix, iy, "• 같은 과목 조건에서도 니즈 벡터에 따라 다른 시안 생성", 17, iw, "#14324F", True)
    pil_para(draw, ix, iy + 60, "• 강의평·시간대·공강·학점 기준을 추천 근거로 제시", 17, iw, "#14324F", True)
    pil_para(draw, ix, iy + 120, "• 더 많은 강의평과 사용자 피드백으로 확장 가능", 17, iw, "#14324F", True)

    ix, iy, iw, ih = pil_card(draw, xs[1], y0, col_w, 276, "SYSTEM PIPELINE")
    steps = ["과목 DB", "강의평 DB", "벡터화", "유사도 계산", "A/B/C 시안"]
    for i, s in enumerate(steps):
        bx = ix + i * 82
        draw.rounded_rectangle((bx, iy + 42, bx + 72, iy + 88), radius=10, fill=["#BDEBFB", "#D9CBFF", "#BEEBE6", "#FFE1A6", "#FFD1CD"][i])
        pil_text(draw, (bx + 8, iy + 56), s, 11, "#14324F", True)
    pil_para(draw, ix, iy + 124, "과목 DB와 강의평 DB를 벡터로 변환하고 유사도와 시간표 제약을 함께 계산한다.", 17, iw)

    ix, iy, iw, ih = pil_card(draw, xs[1], y0 + 296, col_w, 576, "WEB APP FLOW")
    sw = int((iw - 24) / 3)
    for i, (label, name) in enumerate([("1 과목 선택", "course_select.png"), ("2 니즈 입력", "needs_A_1.png"), ("3 시안 확인", "result_A_1.png")]):
        x = ix + i * (sw + 12)
        pil_text(draw, (x, iy), label, 13, "#14324F", True)
        pil_image_fit(img, ASSETS / name, (x, iy + 28, sw, 390))
    pil_para(draw, ix, iy + 448, "전공 과목을 선택하고 기본 정보·개인 니즈를 입력하면 추천 시간표와 추천 근거를 확인한다.", 17, iw)

    ix, iy, iw, ih = pil_card(draw, xs[1], y0 + 892, col_w, 502, "QUESTIONNAIRE SETTINGS")
    half = int((iw - 14) / 2)
    draw.rounded_rectangle((ix, iy, ix + half, iy + 94), radius=14, fill="#BDEBFB")
    pil_text(draw, (ix + 14, iy + 14), "비교군 A", 13, "#14324F", True)
    pil_text(draw, (ix + 14, iy + 42), "부담 최소형", 24, "#14324F", True)
    draw.rounded_rectangle((ix + half + 14, iy, ix + half * 2 + 14, iy + 94), radius=14, fill="#FFD1CD")
    pil_text(draw, (ix + half + 28, iy + 14), "비교군 B", 13, "#14324F", True)
    pil_text(draw, (ix + half + 28, iy + 42), "학습 몰입형", 24, "#14324F", True)
    pil_image_fit(img, ASSETS / "needs_A_2.png", (ix, iy + 120, half, 286))
    pil_image_fit(img, ASSETS / "needs_B_2.png", (ix + half + 14, iy + 120, half, 286))

    ix, iy, iw, ih = pil_card(draw, xs[2], y0, col_w, 660, "RESULTS")
    pil_metric(draw, ix, iy, 116, "비교군 A", "75.8점", "#BDEBFB")
    pil_metric(draw, ix + 132, iy, 116, "비교군 B", "80.0점", "#FFD1CD")
    pil_metric(draw, ix + 264, iy, 142, "탐색 조합", "34,154+", "#BEEBE6")
    pil_text(draw, (ix, iy + 105), "니즈 벡터와 추천 점수 비교", 18, "#14324F", True)
    draw.rounded_rectangle((ix, iy + 142, ix + iw, iy + 390), radius=14, fill="#F7FCFF", outline="#BFEAF8")
    pil_text(draw, (ix + 30, iy + 180), "A: 부담 최소형", 23, "#2FAFE5", True)
    pil_text(draw, (ix + 30, iy + 232), "B: 학습 몰입형", 23, "#FF8A82", True)
    for j, (label, av, bv) in enumerate([("최종", 76, 80), ("강의평", 76, 81), ("교양", 34, 33)]):
        py = iy + 298 + j * 42
        pil_text(draw, (ix + 30, py), label, 14, "#14324F", True)
        draw.rectangle((ix + 100, py + 4, ix + 100 + av * 3, py + 18), fill="#2FAFE5")
        draw.rectangle((ix + 100, py + 22, ix + 100 + bv * 3, py + 36), fill="#FF8A82")
    pil_para(draw, ix, iy + 430, "결론: 같은 전공 4과목·18학점 조건에서도 사용자 니즈에 따라 추천 시안이 달라졌다.", 19, iw, "#14324F", True)
    pil_para(draw, ix, iy + 512, "B 조건은 학습 몰입 선호가 강의평 벡터와 더 높게 맞아 종합 점수가 상승했다.", 16, iw)

    ix, iy, iw, ih = pil_card(draw, xs[2], y0 + 680, col_w, 694, "TIMETABLE RESULTS")
    half = int((iw - 14) / 2)
    pil_text(draw, (ix, iy), "A 대표 시안", 14, "#14324F", True)
    pil_text(draw, (ix + half + 14, iy), "B 대표 시안", 14, "#14324F", True)
    pil_image_fit(img, ASSETS / "result_A_1.png", (ix, iy + 28, half, 530))
    pil_image_fit(img, ASSETS / "result_B_1.png", (ix + half + 14, iy + 28, half, 530))
    pil_para(draw, ix, iy + 580, "대표 결과를 크게 배치해 추천 결과와 시간 분포를 한눈에 비교한다.", 16, iw)

    ix, iy, iw, ih = pil_card(draw, xs[2], y0 + 1394, col_w, 196, "POSTER TAKEAWAY")
    pil_para(draw, ix, iy, "SSU-TIME은 강의평 문장을 수치 벡터로 바꾸고, 내적·노름·코사인 유사도로 사용자 선호와 강의 특성의 일치도를 계산한다.", 17, iw, "#14324F", True)

    pil_text(draw, (margin, h - 24), "SSU-TIME · Advanced AI Mathematics Project Poster · A1 Portrait", 9, "#6B8292")
    img.convert("RGB").save(PNG_OUT, quality=95)


if __name__ == "__main__":
    draw_pdf()
    make_preview()
    print(PDF_OUT)
    print(PNG_OUT)
