# SSU-TIME Backend

## 1. AI 문장 임베딩 설치

가장 간단한 방법은 프로젝트 루트의 아래 파일을 한 번만 더블클릭하는 것입니다.

```text
setup-embedding-model.bat
```

직접 명령어로 설치하려면 프로젝트 폴더에서 실행합니다.

```powershell
python -m pip install -r requirements-backend.txt
```

## 2. 강의평 임베딩 프로필 생성

```powershell
python -m backend.build_embedding_profiles
```

최초 실행에는 임베딩 모델 다운로드와 약 5천 개 강의평 분석 시간이 필요합니다.
분석 결과는 `backend/data/review_embedding_profiles.json`에 저장됩니다.
이후 서버는 캐시를 읽으므로 매번 강의평을 다시 임베딩하지 않습니다.

## 3. 서버 실행

```powershell
python -m backend.main
```

또는 `start-backend-lan.bat`을 실행합니다.

## 상태 확인

```text
http://127.0.0.1:8000/health
```

`embeddingMode` 값의 의미:

- `embedding`: 모델로 강의평을 분석하고 캐시를 생성한 상태
- `embedding-cache`: 생성된 임베딩 프로필 캐시를 사용하는 상태
- `keyword-fallback`: 모델이 설치되지 않아 기존 키워드 분석을 사용하는 상태

## 벡터화 과정

```text
강의평 문장
-> 다국어 Sentence-BERT 384차원 임베딩
-> 7개 특징의 긍정/부정 대표 문장과 코사인 유사도 계산
-> 과제량, 팀플, 시험 부담, 난이도, 학점, 출결, 수업 분위기의 7차원 벡터
-> 기존 키워드 점수 25%를 결합해 고유명사와 짧은 표현 보정
-> 같은 과목/교수 강의평 벡터의 평균
-> 사용자 니즈 벡터와 비교
```
