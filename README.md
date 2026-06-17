# SSU-TIME

강의평 기반 맞춤형 시간표 추천 웹앱입니다.

## GitHub Pages

GitHub Pages 배포용 정적 파일은 `docs/` 폴더에 있습니다.

## Local Backend

추천 알고리즘 백엔드는 로컬에서 실행합니다.

```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

