from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "outputs" / "final-poster"
PDF_OUT = OUT / "ssu_time_algorithm_design.pdf"

PAGE_W, PAGE_H = A4
MARGIN = 48
NAVY = colors.HexColor("#14324F")
INK = colors.HexColor("#263D52")
MUTED = colors.HexColor("#6B8292")
SKY = colors.HexColor("#DDF5FB")
BLUE = colors.HexColor("#2FAFE5")
MINT = colors.HexColor("#BEEBE6")
YELLOW = colors.HexColor("#FFE1A6")
PINK = colors.HexColor("#FFD1CD")
PURPLE = colors.HexColor("#D9CBFF")
LINE = colors.HexColor("#BFEAF8")


def setup_fonts() -> None:
    font_dir = Path("C:/Windows/Fonts")
    pdfmetrics.registerFont(TTFont("Malgun", str(font_dir / "malgun.ttf")))
    pdfmetrics.registerFont(TTFont("Malgun-Bold", str(font_dir / "malgunbd.ttf")))


def tw(text: str, size: float, bold: bool = False) -> float:
    return pdfmetrics.stringWidth(text, "Malgun-Bold" if bold else "Malgun", size)


def draw_text(c: canvas.Canvas, x: float, y: float, text: str, size: float, color=INK, bold=False) -> None:
    c.setFillColor(color)
    c.setFont("Malgun-Bold" if bold else "Malgun", size)
    c.drawString(x, y, text)


def wrap(text: str, size: float, max_w: float, bold: bool = False) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue
        current = ""
        for word in paragraph.split(" "):
            trial = word if not current else f"{current} {word}"
            if tw(trial, size, bold) <= max_w:
                current = trial
                continue
            if current:
                lines.append(current)
            current = word
        if current:
            lines.append(current)
    return lines


class Doc:
    def __init__(self) -> None:
        setup_fonts()
        self.c = canvas.Canvas(str(PDF_OUT), pagesize=A4)
        self.page = 0
        self.y = PAGE_H - MARGIN

    def new_page(self, title: str | None = None) -> None:
        if self.page:
            self.c.showPage()
        self.page += 1
        self.c.setFillColor(SKY)
        self.c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
        self.c.setStrokeColor(colors.Color(0.18, 0.69, 0.90, alpha=0.18))
        self.c.setLineWidth(0.5)
        for x in range(0, int(PAGE_W) + 1, 28):
            self.c.line(x, 0, x, PAGE_H)
        for y in range(0, int(PAGE_H) + 1, 28):
            self.c.line(0, y, PAGE_W, y)
        self.c.setFillColor(colors.white)
        self.c.roundRect(MARGIN - 18, 46, PAGE_W - (MARGIN - 18) * 2, PAGE_H - 92, 22, fill=1, stroke=0)
        self.y = PAGE_H - MARGIN - 18
        if title:
            draw_text(self.c, MARGIN, self.y, title, 24, NAVY, True)
            self.y -= 34
        draw_text(self.c, MARGIN, 26, f"SSU-TIME Algorithm Design · {self.page}", 8.5, MUTED)

    def h1(self, text: str) -> None:
        draw_text(self.c, MARGIN, self.y, text, 28, NAVY, True)
        self.y -= 40

    def h2(self, text: str) -> None:
        if self.y < 135:
            self.new_page()
        draw_text(self.c, MARGIN, self.y, text, 17, NAVY, True)
        self.c.setStrokeColor(LINE)
        self.c.line(MARGIN, self.y - 8, PAGE_W - MARGIN, self.y - 8)
        self.y -= 28

    def p(self, text: str, size: float = 12.2, color=INK, bold=False, gap: float = 12) -> None:
        max_w = PAGE_W - MARGIN * 2
        line_h = size * 1.55
        for line in wrap(text, size, max_w, bold):
            if self.y < 76:
                self.new_page()
            if line:
                draw_text(self.c, MARGIN, self.y, line, size, color, bold)
            self.y -= line_h
        self.y -= gap

    def bullet(self, title: str, body: str, color=BLUE) -> None:
        if self.y < 108:
            self.new_page()
        self.c.setFillColor(color)
        self.c.circle(MARGIN + 5, self.y + 5, 4, fill=1, stroke=0)
        draw_text(self.c, MARGIN + 18, self.y, title, 12.4, NAVY, True)
        self.y -= 20
        for line in wrap(body, 11.2, PAGE_W - MARGIN * 2 - 18):
            draw_text(self.c, MARGIN + 18, self.y, line, 11.2, MUTED)
            self.y -= 16
        self.y -= 8

    def callout(self, title: str, lines: list[str], fill=SKY) -> None:
        h = 36 + len(lines) * 18
        if self.y - h < 72:
            self.new_page()
        x, y, w = MARGIN, self.y - h, PAGE_W - MARGIN * 2
        self.c.setFillColor(fill)
        self.c.roundRect(x, y, w, h, 14, fill=1, stroke=0)
        draw_text(self.c, x + 16, y + h - 24, title, 12.5, NAVY, True)
        yy = y + h - 44
        for line in lines:
            draw_text(self.c, x + 16, yy, line, 10.8, INK)
            yy -= 18
        self.y = y - 18

    def table(self, headers: list[str], rows: list[list[str]], widths: list[float]) -> None:
        row_h = 30
        total_h = row_h * (len(rows) + 1)
        if self.y - total_h < 72:
            self.new_page()
        x, y = MARGIN, self.y - row_h
        self.c.setFillColor(BLUE)
        self.c.roundRect(x, y, sum(widths), row_h, 8, fill=1, stroke=0)
        cx = x
        for header, width in zip(headers, widths):
            draw_text(self.c, cx + 8, y + 10, header, 10.5, colors.white, True)
            cx += width
        y -= row_h
        for idx, row in enumerate(rows):
            self.c.setFillColor(colors.HexColor("#F7FCFF") if idx % 2 == 0 else colors.white)
            self.c.rect(x, y, sum(widths), row_h, fill=1, stroke=0)
            cx = x
            for value, width in zip(row, widths):
                draw_text(self.c, cx + 8, y + 10, value, 9.7, INK)
                cx += width
            y -= row_h
        self.c.setStrokeColor(LINE)
        self.c.rect(x, y + row_h, sum(widths), total_h, fill=0, stroke=1)
        self.y = y - 12

    def flow(self, labels: list[str]) -> None:
        if self.y < 150:
            self.new_page()
        x = MARGIN
        y = self.y - 58
        box_w = (PAGE_W - MARGIN * 2 - 56) / len(labels)
        fills = [PINK, YELLOW, MINT, PURPLE, colors.HexColor("#BDEBFB")]
        for i, label in enumerate(labels):
            bx = x + i * (box_w + 14)
            self.c.setFillColor(fills[i % len(fills)])
            self.c.roundRect(bx, y, box_w, 46, 11, fill=1, stroke=0)
            draw_text(self.c, bx + (box_w - tw(label, 10.5, True)) / 2, y + 17, label, 10.5, NAVY, True)
            if i < len(labels) - 1:
                self.c.setStrokeColor(BLUE)
                self.c.setLineWidth(2)
                self.c.line(bx + box_w + 3, y + 23, bx + box_w + 12, y + 23)
        self.y = y - 24

    def save(self) -> None:
        self.c.save()


def build() -> None:
    doc = Doc()
    doc.new_page()
    doc.h1("SSU-TIME 알고리즘 및 데이터 설계 설명서")
    doc.p("강의평 기반 맞춤형 시간표 추천 시스템", 18, NAVY, True, 8)
    doc.p("팀 너시간표내꺼 · 조세진, 박시우, 안민기, 윤서준, 이동연 · AI소프트웨어학부", 11.5, MUTED, False, 8)
    doc.p("고급AI수학 · 김창훈 교수님 · 2026.06.18", 11.5, MUTED, False, 22)
    doc.callout(
        "한 줄 요약",
        [
            "사용자가 선택한 전공 과목과 니즈를 벡터로 표현한다.",
            "강의평 문장도 7차원 강의 특성 벡터로 변환한다.",
            "두 벡터의 유사도와 시간표 제약을 함께 계산해 A/B/C 시안을 만든다.",
        ],
        colors.HexColor("#E8F8FF"),
    )
    doc.h2("1. 시스템 전체 흐름")
    doc.flow(["과목 선택", "니즈 입력", "강의평 벡터화", "조합 탐색", "A/B/C 추천"])
    doc.bullet("입력", "사용자는 듣고 싶은 전공 과목, 목표 학점, 시간대 선호, 공강 선호, 수업 성향 질문지, 교양 추천 여부와 키워드를 입력한다.", BLUE)
    doc.bullet("분석", "백엔드는 강의평을 과목-교수 단위로 묶고, 리뷰 문장에서 과제·팀플·시험·난이도·학점·출석·분위기 특성을 추출한다.", MINT)
    doc.bullet("출력", "시간 충돌이 없는 후보 조합만 남긴 뒤, 종합 점수 기준으로 A안, 공강 기준으로 B안, 시간대 기준으로 C안을 제시한다.", YELLOW)

    doc.h2("2. 데이터는 어디서 가져왔는가")
    doc.table(
        ["데이터", "출처", "정제 후 사용"],
        [
            ["과목 시간표", "2026-1 강의시간표 XLSX", "401개 과목"],
            ["전공 과목", "AI대학 AI소프트웨어학부 시간표", "92개"],
            ["교양 과목", "교양선택 영역별 시간표", "309개"],
            ["강의평", "에브리타임 강의실 API/수집 결과", "5,113개 리뷰"],
            ["강의 프로필", "과목명+교수명 기준 리뷰 그룹화", "225개 프로필"],
            ["사용자 니즈", "웹앱 질문지 응답", "추천 요청 시 실시간 입력"],
        ],
        [82, 205, 170],
    )
    doc.bullet("과목 DB 정제", "원본 468행에서 중복 67행을 제거해 401개 행으로 정제했다. 각 행은 과목명, 교수명, 이수구분, 학점, 수업 시간, 강의실 정보를 가진다.", BLUE)
    doc.bullet("강의평 DB 정제", "api_reviews.xlsx에는 course_name, professor, lecture_id, rating, review_text, semester 등이 저장된다. 백엔드는 같은 과목명과 교수명을 묶어 하나의 LectureProfile로 만든다.", MINT)
    doc.bullet("교양 추천 조건", "사용자가 교양을 넣겠다고 선택하면 course_group=liberal, completion_type=교선 과목만 자동 추천 후보로 사용한다. 키워드가 없으면 랜덤 교양 후보를 섞고, 키워드가 있으면 TF-IDF 유사도를 계산한다.", YELLOW)

    doc.new_page("3. 강의평을 벡터로 바꾸는 방법")
    doc.p("강의평 문장은 그대로는 계산할 수 없기 때문에, 리뷰 문장에서 수업 특성을 나타내는 키워드를 세어 0~1 사이의 수치로 변환한다.", 12.5)
    doc.table(
        ["차원", "의미", "질문지와 연결"],
        [
            ["assignment_load", "과제량", "과제가 많은/적은 수업 선호"],
            ["team_presentation", "팀플·발표", "팀플/발표 선호 또는 회피"],
            ["exam_load", "시험 부담", "시험 중심 또는 시험 부담 적게"],
            ["difficulty", "난이도", "깊이 있는 수업 또는 부담 적은 수업"],
            ["grade_generosity", "학점 후함", "학점 후한 수업 또는 내용 중심"],
            ["attendance_strictness", "출석 엄격함", "출석 관리 엄격/느슨"],
            ["fun_relaxed", "수업 분위기", "재미있고 편한 수업 또는 체계적 수업"],
        ],
        [118, 120, 219],
    )
    doc.callout(
        "강의 벡터",
        [
            "l = (l_1, l_2, ..., l_7)",
            "예: 과제 많음=0.82, 시험 부담=0.77, 학점 후함=0.40 ...",
            "리뷰가 없는 강의는 모든 차원을 0.5로 두어 중립값으로 처리한다.",
        ],
        colors.HexColor("#F7FCFF"),
    )
    doc.bullet("키워드 기반 점수화", "각 특성마다 긍정 키워드와 부정 키워드를 두고, 리뷰 텍스트에서 등장 횟수를 센다. pos-neg 값을 sigmoid 함수에 넣어 0~1 범위로 정규화한다.", BLUE)
    doc.bullet("별점 보정", "별점은 수업 분위기와 학점 후함 차원에 일부 반영한다. 예를 들어 별점이 높으면 fun_relaxed와 grade_generosity가 약간 상승한다.", MINT)
    doc.bullet("프로필 평균", "같은 과목-교수 조합의 여러 리뷰 벡터를 평균내어 하나의 강의 프로필 벡터를 만든다. 이것이 시간표 추천 때 비교되는 강의 대표값이다.", YELLOW)

    doc.h2("4. 사용자 니즈 벡터 설계")
    doc.p("질문지 응답은 사용자가 원하는 수업 성향을 7차원 목표 벡터 u로 바꾼다. 상관없음은 해당 차원의 가중치를 낮추거나 비교에서 제외한다.", 12.5)
    doc.callout(
        "사용자 벡터와 가중치",
        [
            "u = (u_1, u_2, ..., u_7)",
            "w = (w_1, w_2, ..., w_7)",
            "u'_i = w_i u_i,   l'_i = w_i l_i",
        ],
        colors.HexColor("#E8F8FF"),
    )
    doc.bullet("목표값 예시", "과제가 적은 수업을 선호하면 assignment_load 목표값을 0.1로 둔다. 깊이 있는 수업을 선호하면 difficulty 목표값을 0.82로 둔다.", BLUE)
    doc.bullet("가중치 역할", "사용자가 상관없음을 선택한 항목은 비교에서 중요하지 않게 처리한다. 즉 모든 질문이 같은 영향력을 갖지 않고, 사용자가 답한 항목 중심으로 비교된다.", MINT)

    doc.new_page("5. 선형대수적으로 어떻게 계산하는가")
    doc.p("이 프로젝트의 핵심 선형대수 개념은 벡터, 내적, 노름, 코사인 유사도다. 강의평과 사용자 니즈를 같은 차원의 벡터 공간에 배치한 뒤, 두 벡터가 얼마나 같은 방향을 보는지 계산한다.", 12.5)
    doc.callout(
        "코사인 유사도",
        [
            "cos(theta) = (u' dot l') / (||u'|| ||l'||)",
            "u': 가중치가 적용된 사용자 니즈 벡터",
            "l': 가중치가 적용된 강의 특성 벡터",
            "값이 1에 가까울수록 사용자 니즈와 강의 특성이 잘 맞는다.",
        ],
        colors.HexColor("#F7FCFF"),
    )
    doc.callout(
        "강의 적합도",
        [
            "direction = (cos(theta) + 1) / 2",
            "distance = 평균(1 - |u_i - l_i|)",
            "lecture_fit = 0.55 direction + 0.45 distance",
        ],
        colors.HexColor("#E8F8FF"),
    )
    doc.bullet("왜 코사인 유사도인가", "벡터의 크기보다 방향을 비교할 수 있다. 즉 과제, 시험, 분위기 등 여러 특성의 상대적인 패턴이 사용자 니즈와 비슷한지를 볼 수 있다.", BLUE)
    doc.bullet("왜 거리 점수를 함께 쓰는가", "코사인 유사도는 방향이 비슷하면 점수가 높지만, 각 차원의 실제 값 차이를 충분히 반영하지 못할 수 있다. 그래서 차원별 차이를 distance 점수로 보완했다.", MINT)
    doc.bullet("키워드 교양 추천", "교양 키워드는 TF-IDF sparse vector로 바꾸고, 교양 과목 문서 벡터와 sparse cosine을 계산한다. 키워드가 과목명/영역명에 직접 포함되면 보너스를 준다.", YELLOW)

    doc.h2("6. 시간표 조합 알고리즘")
    doc.flow(["전공 후보 생성", "교양 후보 생성", "충돌 제거", "학점 제한", "점수 정렬"])
    doc.bullet("전공 후보", "사용자가 선택한 과목명과 이수구분에 맞는 모든 분반·교수 후보를 찾는다. 각 후보는 강의평 벡터와 사용자 벡터의 lecture_fit을 가진다.", BLUE)
    doc.bullet("시간 충돌 제거", "요일별 수업 구간을 start/end 분 단위로 변환하고, 같은 요일에서 이전 수업 종료 시간이 다음 수업 시작보다 늦으면 충돌로 제거한다.", MINT)
    doc.bullet("학점 제한", "사용자가 입력한 목표 학점을 넘는 조합은 제외한다. 남는 학점이 있으면 교양 후보를 추가하되, 목표 학점을 초과하지 않는다.", YELLOW)
    doc.bullet("탐색 방식", "전공 후보는 cartesian product로 조합하고, 교양은 backtracking으로 가능한 조합을 확장한다. 중복 과목명과 시간 충돌이 있는 조합은 즉시 버린다.", PURPLE)

    doc.new_page("7. 최종 점수와 A/B/C 시안 선정")
    doc.p("한 시간표 T의 점수는 강의평 적합도뿐 아니라 목표 학점, 시간대, 공강, 교양 키워드 적합도를 함께 반영한다.", 12.5)
    doc.callout(
        "최종 추천 점수",
        [
            "S(T) = 0.32 S_review + 0.12 S_time + 0.12 S_dayoff",
            "       + 0.09 S_keyword + 0.35 S_credit",
            "S_review: 각 강의 lecture_fit 평균",
            "S_credit: 목표 학점에 가까운 정도, 목표 초과는 0점",
        ],
        colors.HexColor("#F7FCFF"),
    )
    doc.table(
        ["항목", "계산 기준", "가중치"],
        [
            ["강의평", "사용자 니즈 벡터와 강의 벡터의 적합도 평균", "0.32"],
            ["시간대", "아침형/저녁형 선호와 평균 시작 시간의 일치", "0.12"],
            ["공강", "요일 몰아듣기/분산 선호와 실제 사용 요일 수", "0.12"],
            ["교양 키워드", "TF-IDF 키워드 유사도 또는 랜덤 교양 중립값", "0.09"],
            ["목표 학점", "목표 학점에 가까울수록 높고, 초과하면 제외", "0.35"],
        ],
        [90, 300, 66],
    )
    doc.bullet("A안", "전체 종합 점수 S(T)가 가장 높은 균형형 시안이다.", BLUE)
    doc.bullet("B안", "공강 점수와 종합 점수를 함께 고려해 특정 요일에 수업을 몰아주는 시안이다.", MINT)
    doc.bullet("C안", "시간대 점수와 종합 점수를 함께 고려해 아침형/저녁형 선호에 더 맞춘 시안이다.", YELLOW)

    doc.h2("8. 백엔드 API와 실행 구조")
    doc.table(
        ["API", "역할"],
        [
            ["GET /health", "과목 수와 강의평 프로필 수를 확인한다."],
            ["GET /courses?q=", "과목명 검색 결과를 반환한다."],
            ["POST /recommend", "선택 과목과 니즈를 받아 A/B/C 시간표 시안을 계산한다."],
            ["GET /debug/last-recommend", "마지막 추천 요청과 결과를 발표/디버깅용으로 확인한다."],
        ],
        [160, 296],
    )
    doc.bullet("프론트엔드", "사용자는 모바일 웹앱에서 과목을 담고 질문지에 답한다. 추천 시간표 보러가기를 누르면 /recommend 요청이 백엔드로 전송된다.", BLUE)
    doc.bullet("백엔드", "FastAPI 서버가 요청을 받고 RecommendationEngine이 과목 후보, 강의평 벡터, 시간표 제약을 계산해 JSON으로 결과를 반환한다.", MINT)

    doc.new_page("9. 발표할 때 강조할 포인트")
    doc.bullet("선형대수 프로젝트로서의 핵심", "문장을 단순히 감으로 분류한 것이 아니라, 사용자 니즈와 강의평을 같은 벡터 공간에 놓고 내적·노름·코사인 유사도로 비교했다.", BLUE)
    doc.bullet("설명 가능한 추천", "LLM이 블랙박스로 시간표를 찍어주는 방식이 아니라, 강의평/시간대/공강/학점/키워드 점수가 각각 계산되어 추천 근거를 설명할 수 있다.", MINT)
    doc.bullet("현실적인 제약 반영", "시간표 추천은 점수만 높다고 끝나지 않는다. 실제 수업 시간 충돌, 목표 학점 초과, 교양 여부, 중복 과목명을 모두 제약으로 처리했다.", YELLOW)
    doc.bullet("데이터 기반 결과", "정제된 과목 DB 401개, 교양 후보 309개, 에브리타임 리뷰 5,113개, 과목-교수 프로필 225개를 바탕으로 추천 결과를 만든다.", PURPLE)
    doc.callout(
        "발표용 한 문장",
        [
            "SSU-TIME은 강의평 문장을 7차원 벡터로 바꾸고,",
            "사용자 니즈 벡터와의 코사인 유사도를 계산해",
            "시간 충돌이 없는 최적 시간표 시안을 추천하는 시스템입니다.",
        ],
        colors.HexColor("#E8F8FF"),
    )
    doc.h2("10. 한계와 개선 방향")
    doc.bullet("현재 한계", "키워드 기반 감성/특성 추출이므로 문맥을 완전히 이해하지는 못한다. 예를 들어 반어법이나 복잡한 문장은 오분류될 수 있다.", BLUE)
    doc.bullet("개선 방향", "추후에는 KoBERT, Sentence-BERT 같은 한국어 임베딩 모델을 적용해 리뷰 문장을 더 정교한 의미 벡터로 바꿀 수 있다.", MINT)
    doc.bullet("프로젝트 의미", "현재 버전은 선형대수 개념이 드러나는 해석 가능한 추천 모델이며, AI 모델로 확장하기 전의 명확한 수학적 기준선 역할을 한다.", YELLOW)

    doc.save()


if __name__ == "__main__":
    build()
    print(PDF_OUT)
