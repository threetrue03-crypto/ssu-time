# SSU-TIME

> 강의평 기반 맞춤형 시간표 추천 시스템

SSU-TIME은 사용자가 선택한 전공 과목과 시간표 선호도를 바탕으로 강의평을 분석하고, 시간 충돌과 목표 학점을 고려해 A/B/C 시간표 시안을 추천하는 웹 애플리케이션입니다.

## 프로젝트 정보

- 팀명: 너시간표내꺼
- 팀원: 조세진, 박시우, 안민기, 윤서준, 이동연
- 소속: 숭실대학교 AI소프트웨어학부
- 과목: 고급AI수학
- 담당 교수: 김창훈 교수님
- 기준 학기: 2026학년도 1학기

## 주요 기능

- 과목명 검색 및 전공 과목 선택
- 선택 과목의 학점 합산
- 시간대, 공강, 목표 학점 등 기본 조건 입력
- 과제량, 팀플, 시험, 난이도, 학점, 출결, 분위기 선호 입력
- 강의평 기반 교수 및 강의 적합도 계산
- 교양 키워드 기반 교양 과목 자동 추천
- 시간 충돌과 목표 학점을 만족하는 A/B/C 시간표 생성
- 추천 이유와 항목별 적합도 제공
- 선택한 시간표를 PNG 이미지로 저장

## 시스템 흐름

```text
과목 선택
-> 기본 정보 입력
-> 개인 니즈 입력
-> 강의평 문장 임베딩
-> 강의 성향 벡터 생성
-> 사용자 니즈 벡터와 비교
-> 시간 충돌 및 목표 학점 검사
-> A/B/C 시간표 추천
```

## AI 및 선형대수

### 1. 문장 임베딩

강의평은 다국어 Sentence-BERT 계열 모델인
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`를 통해 384차원 의미 벡터로 변환합니다.

```text
강의평 문장 -> Sentence-BERT -> 384차원 임베딩 벡터
```

### 2. 7차원 강의 성향 공간

사용자 질문과 강의평을 다음과 같은 동일한 7차원 특징 공간에 배치합니다.

```text
[과제량, 팀플·발표, 시험 부담, 난이도, 학점, 출결, 수업 분위기]
```

각 특징에는 긍정·부정 기준 문장을 준비합니다. 강의평 임베딩과 기준 문장 임베딩 사이의 코사인 유사도를 계산해 384차원 벡터를 7차원 강의 성향 벡터로 변환합니다.

```math
s_i^+ = \cos(\mathbf{e}, \mathbf{p}_i), \qquad
s_i^- = \cos(\mathbf{e}, \mathbf{n}_i)
```

```math
c_i = \sigma\left(10(s_i^+ - s_i^-)\right)
```

짧은 은어와 학교식 표현을 보완하기 위해 임베딩 점수와 키워드 점수를 결합합니다.

```math
\mathbf{c}_{final}
=0.75\mathbf{c}_{embedding}
+0.25\mathbf{c}_{keyword}
```

### 3. 사용자 니즈 벡터

질문지에서 낮은 성향 선호는 `0.1`, 높은 성향 선호는 `0.9`, 상관없음은 중립값 `0.5`로 표현합니다. 상관없음을 선택한 항목은 가중치 마스크를 `0`으로 설정해 비교에서 제외합니다.

```math
\mathbf{u}'=\mathbf{w}\odot\mathbf{u}, \qquad
\mathbf{c}'=\mathbf{w}\odot\mathbf{c}
```

- `u`: 사용자 니즈 벡터
- `c`: 강의 성향 벡터
- `w`: 질문 반영 여부를 나타내는 가중치 마스크

### 4. 강의 적합도

벡터의 방향뿐 아니라 각 특징 값의 차이도 반영하기 위해 코사인 유사도와 원소별 거리 점수를 함께 사용합니다.

```math
S_{lecture}
=0.55S_{cosine}
+0.45S_{distance}
```

### 5. 시간표 최종 점수

시간 충돌을 제거하고 목표 학점 이하의 조합만 남긴 뒤 다음 가중합으로 시간표를 평가합니다.

```math
S
=0.32S_{lecture}
+0.12S_{time}
+0.12S_{dayoff}
+0.09S_{keyword}
+0.35S_{credit}
```

- A안: 전체 점수가 높은 균형형 시간표
- B안: 공강 조건을 우선한 시간표
- C안: 선호 시간대를 우선한 시간표

## 기술 스택

### Frontend

- HTML5
- CSS3
- Vanilla JavaScript
- Canvas API

### Backend

- Python
- FastAPI
- Uvicorn
- Pydantic

### AI 및 데이터 처리

- Sentence-Transformers
- `paraphrase-multilingual-MiniLM-L12-v2`
- NumPy
- OpenPyXL
- TF-IDF
- 코사인 유사도

## 프로젝트 구조

```text
SSU-TIME/
├─ backend/                    # FastAPI와 추천 알고리즘
├─ docs/                       # GitHub Pages용 프론트엔드
├─ outputs/
│  ├─ course-data-cleaned/     # 정제된 과목 데이터
│  ├─ final-poster/            # A1 포스터와 설명서
│  └─ ssu-time-start-screen/   # 프론트엔드 원본
├─ scraper/                    # 강의평 수집 및 과목 목록 생성 코드
├─ requirements-backend.txt
├─ setup-embedding-model.bat
├─ start-backend-lan.bat
└─ start-frontend-lan.bat
```

## 로컬 실행

### 1. 임베딩 모델 설치 및 프로필 생성

프로젝트 루트에서 `setup-embedding-model.bat`을 한 번 실행합니다.

직접 실행하려면:

```powershell
python -m pip install -r requirements-backend.txt
python -m backend.build_embedding_profiles
```

### 2. 백엔드 실행

`start-backend-lan.bat`을 실행하거나 다음 명령을 사용합니다.

```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

상태 확인:

```text
http://localhost:8000/health
```

`embeddingMode`가 `embedding` 또는 `embedding-cache`이면 문장 임베딩이 적용된 상태입니다.

### 3. 프론트엔드 실행

`start-frontend-lan.bat`을 실행하거나:

```powershell
python -m http.server 5500 --bind 0.0.0.0 --directory outputs/ssu-time-start-screen
```

노트북에서 접속:

```text
http://localhost:5500
```

같은 Wi-Fi의 휴대폰에서는 노트북의 내부 IP와 `5500` 포트로 접속합니다.

## GitHub Pages

정적 프론트엔드는 `docs/` 폴더에서 배포합니다.

```text
Settings -> Pages -> Deploy from a branch -> main -> /docs
```

GitHub Pages는 Python 백엔드를 실행하지 않습니다. 정적 화면은 Pages에서 확인할 수 있지만 실제 추천 기능을 사용하려면 별도의 FastAPI 서버가 실행 중이어야 합니다.

## 데이터 출처

- 2026학년도 1학기 숭실대학교 강의시간표
- 수집한 강의평 데이터

강의평 원문, 로그인 정보, 쿠키 및 세션 파일은 저장소에 포함하지 않습니다. 수집 코드는 해당 서비스의 이용약관과 개인정보 보호 기준을 확인한 뒤 연구 및 교육 목적에 맞게 사용해야 합니다.

## 문서

- A1 포스터: `outputs/final-poster/poster_a1_revised.pdf`
- 알고리즘 설계 설명서: `outputs/final-poster/ssu_time_algorithm_design.pdf`

## 유의사항

현재 사용자 벡터 값과 최종 점수 계수는 프로젝트의 초기 휴리스틱 설정입니다. 향후 사용자 만족도 데이터를 축적하면 지도학습이나 회귀분석을 통해 값을 최적화할 수 있습니다.
