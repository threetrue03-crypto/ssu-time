# SSU-TIME

> 강의평 기반 맞춤형 시간표 추천 시스템  
> 사용자가 고른 전공 과목, 목표 학점, 시간대 선호, 공강 선호, 수업 성향 니즈를 바탕으로 2026학년도 1학기 시간표 시안을 추천하는 웹 애플리케이션입니다.

SSU-TIME은 단순히 시간이 겹치지 않는 시간표를 나열하는 도구가 아니라, 강의평 문장을 벡터화하여 사용자의 선호와 비교하고, 그 결과를 시간표 조합 알고리즘에 반영하는 것을 목표로 합니다.

## 제작자

- 조세진

## 핵심 기능

- 과목명 검색을 통한 전공 과목 선택
- 선택한 과목의 총 학점 계산
- 목표 학점, 선호 시간대, 공강 선호 입력
- 과제량, 팀플/발표, 시험 부담, 난이도, 학점, 출석, 수업 분위기 니즈 입력
- 교양 과목 자동 추천 여부 선택
- 강의평 기반 강의 성향 벡터 생성
- 사용자 니즈 벡터와 강의 성향 벡터의 유사도 계산
- 시간 충돌과 목표 학점을 만족하는 A/B/C 시간표 시안 생성
- 추천 결과의 근거 시각화
- 선택한 시간표를 PNG 이미지로 저장

## 사용 흐름

```text
과목 선택
-> 기본 정보 입력
-> 개인 니즈 입력
-> 강의평 벡터화
-> 사용자 니즈 벡터와 강의 성향 벡터 비교
-> 시간 충돌 제거
-> 목표 학점 이하의 조합 탐색
-> A/B/C 시간표 시안 추천
```

## 데이터 구성

SSU-TIME은 두 종류의 데이터를 사용합니다.

```text
2026학년도 1학기 강의 시간표
-> 과목명, 교수명, 이수구분, 학점, 요일/시간, 강의실 정보

강의평 데이터
-> 과목명, 교수명, 평점, 강의평 문장
```

정제된 과목 데이터는 `outputs/course-data-cleaned/ssu_time_courses_clean.json`을 기준으로 사용합니다. 강의평 원본 데이터와 로그인 정보, 쿠키, 세션 파일은 개인정보와 서비스 이용 정책을 고려하여 저장소에 포함하지 않습니다.

## 추천 알고리즘

### 1. 강의평 문장 임베딩

강의평 문장은 먼저 다국어 Sentence-BERT 계열 모델인 `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`를 통해 384차원 문장 벡터로 변환합니다.

```math
\mathbf{e} = \mathrm{SBERT}(\text{review}) \in \mathbb{R}^{384}
```

이 단계의 목적은 `"과제가 너무 많다"`, `"매주 제출할 게 있다"`, `"할 일이 계속 나온다"`처럼 표현은 다르지만 의미가 비슷한 문장을 비슷한 벡터로 표현하는 것입니다.

### 2. 384차원 문장 벡터를 7차원 강의 성향 공간으로 변환

사용자 설문과 직접 비교하기 위해 강의평 벡터를 다음 7개 특징 공간으로 변환합니다.

```text
[과제량, 팀플/발표, 시험 부담, 난이도, 학점 후함, 출석 엄격함, 수업 분위기]
```

각 특징마다 긍정 기준 문장과 부정 기준 문장을 준비합니다. 예를 들어 과제량 특징은 다음과 같은 기준을 가집니다.

```text
positive: 과제가 많고 매주 제출해야 하는 수업이다.
negative: 과제가 거의 없고 부담이 적은 수업이다.
```

강의평 벡터와 기준 문장 벡터 사이의 코사인 유사도를 비교하여 해당 특징의 점수를 계산합니다.

```math
s_i^+ = \cos(\mathbf{e}, \mathbf{p}_i), \qquad
s_i^- = \cos(\mathbf{e}, \mathbf{n}_i)
```

```math
c_i = \sigma(10(s_i^+ - s_i^-))
```

여기서 `p_i`는 i번째 특징의 긍정 기준 벡터, `n_i`는 부정 기준 벡터입니다. 이렇게 만들어진 강의 성향 벡터는 다음과 같습니다.

```math
\mathbf{c} = [c_1,c_2,\dots,c_7] \in \mathbb{R}^{7}
```

### 3. 키워드 기반 보정

임베딩 모델이 모든 표현을 완벽하게 해석하지 못할 수 있으므로, 명확한 단어 패턴을 보조적으로 사용합니다. 최종 강의 성향 벡터는 임베딩 기반 점수와 키워드 기반 점수를 결합합니다.

```math
\mathbf{c}_{final}
=0.75\mathbf{c}_{embedding}
+0.25\mathbf{c}_{keyword}
```

즉, 핵심 판단은 AI 임베딩이 담당하고, 키워드 규칙은 보정 장치로만 사용합니다.

### 4. 사용자 니즈 벡터 생성

사용자의 설문 응답도 같은 7차원 공간에 배치합니다.

```math
\mathbf{u} = [u_1,u_2,\dots,u_7] \in \mathbb{R}^{7}
```

예를 들어 사용자가 과제가 적은 수업을 원하면 과제량 축은 낮은 값에 가까워지고, 시험 중심 수업을 원하면 시험 부담 축은 높은 값에 가까워집니다. `상관없어요`를 선택한 항목은 비교에서 큰 영향을 주지 않도록 가중치 마스크를 0으로 둡니다.

```math
\mathbf{u}'=\mathbf{w}\odot\mathbf{u}, \qquad
\mathbf{c}'=\mathbf{w}\odot\mathbf{c}_{final}
```

- `u`: 사용자 니즈 벡터
- `c_final`: 강의 성향 벡터
- `w`: 사용자가 중요하게 고른 항목만 반영하는 가중치 마스크
- `⊙`: 원소별 곱셈

### 5. 강의 적합도 계산

사용자 니즈와 강의 성향이 얼마나 비슷한지는 코사인 유사도와 원소별 거리 점수를 함께 사용해 계산합니다.

```math
S_{cosine}
=\frac{\mathbf{u}'\cdot\mathbf{c}'}
{\|\mathbf{u}'\|\|\mathbf{c}'\|}
```

```math
S_{lecture}
=0.55S_{cosine}
+0.45S_{distance}
```

코사인 유사도는 두 벡터의 방향이 비슷한지 보고, 거리 점수는 각 특징 값이 실제로 얼마나 가까운지 봅니다. 두 값을 함께 사용하면 전체적인 선호 방향과 세부 특징 차이를 동시에 반영할 수 있습니다.

### 6. 시간표 최종 점수

시간표 조합은 강의평 적합도만으로 결정하지 않습니다. 목표 학점, 시간대 선호, 공강 선호, 교양 키워드 적합도도 함께 반영합니다.

```math
S
=0.32S_{lecture}
+0.12S_{time}
+0.12S_{dayoff}
+0.09S_{keyword}
+0.35S_{credit}
```

- `S_lecture`: 강의평과 사용자 니즈의 적합도
- `S_time`: 아침형/저녁형 선호와 실제 수업 시간의 적합도
- `S_dayoff`: 공강 만들기/분산 선호의 적합도
- `S_keyword`: 교양 키워드와 교양 과목의 적합도
- `S_credit`: 목표 학점에 얼마나 가깝게 구성되었는지

시간이 겹치는 조합은 최종 후보에서 제외하고, 목표 학점을 초과하는 조합도 제거합니다.

## 선형대수 개념

이 프로젝트에서 선형대수는 단순한 장식이 아니라 추천 과정의 중심 역할을 합니다.

- 문장을 고차원 벡터로 표현
- 강의평 벡터와 기준 문장 벡터의 코사인 유사도 계산
- 384차원 임베딩 공간을 7차원 특징 공간으로 변환
- 사용자 니즈 벡터와 강의 성향 벡터의 내적 계산
- 가중치 마스크를 이용한 원소별 곱셈
- 여러 평가 항목을 가중합하여 최종 점수 계산

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
- OpenPyXL
- NumPy

### AI / Algorithm

- Sentence-Transformers
- `paraphrase-multilingual-MiniLM-L12-v2`
- Sentence-BERT 문장 임베딩
- Cosine Similarity
- TF-IDF 기반 교양 키워드 매칭
- Backtracking 기반 시간표 조합 탐색

## 프로젝트 구조

```text
SSU-TIME/
├─ backend/                    # FastAPI 추천 서버
├─ docs/                       # GitHub Pages 배포용 정적 프론트엔드
├─ outputs/
│  ├─ course-data-cleaned/     # 정제된 과목 데이터
│  ├─ final-poster/            # A1 포스터와 알고리즘 설명 자료
│  └─ ssu-time-start-screen/   # 로컬 실행용 프론트엔드
├─ scraper/                    # 강의평 수집 및 대상 생성 코드
├─ requirements-backend.txt
├─ setup-embedding-model.bat
├─ start-backend-lan.bat
└─ start-frontend-lan.bat
```

## 로컬 실행 방법

### 1. AI 임베딩 모델 설치

처음 한 번만 실행합니다.

```powershell
setup-embedding-model.bat
```

직접 실행하려면 다음 명령을 사용합니다.

```powershell
python -m pip install -r requirements-backend.txt
python -m backend.build_embedding_profiles
```

### 2. 백엔드 실행

```powershell
start-backend-lan.bat
```

또는 직접 실행합니다.

```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

상태 확인:

```text
http://localhost:8000/health
```

`embeddingMode`가 `embedding` 또는 `embedding-cache`이면 문장 임베딩 기반 분석이 적용된 상태입니다. `keyword-fallback`이면 임베딩 모델이 설치되지 않아 키워드 기반 보정 로직만 사용 중인 상태입니다.

### 3. 프론트엔드 실행

```powershell
start-frontend-lan.bat
```

또는 직접 실행합니다.

```powershell
python -m http.server 5500 --bind 0.0.0.0 --directory outputs/ssu-time-start-screen
```

노트북에서 접속:

```text
http://localhost:5500
```

같은 Wi-Fi 또는 핫스팟에 연결된 휴대폰에서는 노트북의 내부 IP를 사용합니다.

```text
http://노트북IP:5500
```

## GitHub Pages 배포

정적 프론트엔드는 `docs/` 폴더에서 배포할 수 있습니다.

```text
Settings -> Pages -> Deploy from a branch -> main -> /docs
```

주의할 점은 GitHub Pages가 Python 백엔드를 실행하지 않는다는 것입니다. 따라서 GitHub Pages에서는 정적 화면을 확인할 수 있고, 실제 추천 계산까지 사용하려면 FastAPI 백엔드 서버가 별도로 실행되어야 합니다.

## 데이터와 개인정보

강의평 데이터는 추천 모델을 만들기 위한 연구 및 교육 목적의 데이터로 사용됩니다. 저장소에는 다음 자료를 포함하지 않습니다.

- 로그인 아이디와 비밀번호
- 쿠키와 세션 정보
- `.env` 파일
- 원본 강의평 수집 결과 파일
- 개인을 식별할 수 있는 민감 정보

강의평 수집 코드는 `scraper/` 폴더에 있으나, 실제 사용 시에는 대상 서비스의 이용 약관과 개인정보 보호 기준을 확인해야 합니다.

## 한계와 개선 방향

현재 사용자 벡터 값과 최종 가중치는 초기 휴리스틱으로 설계되었습니다. 실제 사용자 만족도 데이터가 충분히 쌓이면 다음 방식으로 개선할 수 있습니다.

- 추천 결과 선택 로그 기반 가중치 재학습
- 사용자 만족도 설문을 이용한 회귀 모델 학습
- 강의평 라벨링 데이터 기반 분류 모델 고도화
- 시간표 추천 결과의 다양성 보장 알고리즘 추가
- 실제 수강 가능 여석과 폐강 여부 반영

## 발표 자료

- A1 포스터: `outputs/final-poster/poster_a1_revised.pdf`
- 알고리즘 설계 설명서: `outputs/final-poster/ssu_time_algorithm_design.pdf`

## 라이선스

본 프로젝트는 조세진이 제작한 SSU-TIME 웹 애플리케이션입니다.
