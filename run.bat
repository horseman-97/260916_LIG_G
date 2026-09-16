@echo off
chcp 65001 > nul
title LIG DNA 스마트 투두 앱 실행기

echo ========================================================
echo   🚀 LIG DNA 스마트 투두 (Smart Todo App) 시작 중...
echo ========================================================
echo.

cd /d "%~dp0"

:: Check for python executable
set PYTHON_CMD=python
python --version >nul 2>&1
if errorlevel 1 (
    set PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)

echo [1/2] 필수 패키지 확인 중...
%PYTHON_CMD% -m pip install -r requirements.txt --quiet

echo [2/2] 브라우저 자동 오픈 및 웹 서버 구동 중...
start http://127.0.0.1:5000

echo.
echo ========================================================
echo   접속 주소: http://127.0.0.1:5000
echo   종료하려면 이 창에서 Ctrl + C 를 누르세요.
echo ========================================================
echo.

%PYTHON_CMD% app.py

pause
