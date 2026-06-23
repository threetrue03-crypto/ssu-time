@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo [1/2] AI 문장 임베딩 라이브러리를 설치합니다.
python -m pip install -r requirements-backend.txt
if errorlevel 1 (
  echo.
  echo 설치에 실패했습니다. 인터넷 연결과 Python 버전을 확인해주세요.
  pause
  exit /b 1
)

echo.
echo [2/2] 강의평을 7차원 임베딩 프로필로 변환합니다.
python -m backend.build_embedding_profiles
if errorlevel 1 (
  echo.
  echo 강의평 분석에 실패했습니다.
  pause
  exit /b 1
)

echo.
echo 설정이 완료되었습니다. 이제 start-backend-lan.bat을 실행하세요.
pause
