@echo off
setlocal
cd /d "%~dp0"

if not exist "backend\.venv\Scripts\python.exe" (
    echo [ERROR] Python virtualenv not found at backend\.venv
    echo Run setup first.
    pause
    exit /b 1
)

if not exist "frontend\node_modules" (
    echo [ERROR] frontend\node_modules not found.
    echo Run "cd frontend && npm install" first.
    pause
    exit /b 1
)

echo Running Django migrations...
backend\.venv\Scripts\python.exe backend\manage.py migrate --noinput
if errorlevel 1 (
    echo [ERROR] Migrations failed.
    pause
    exit /b 1
)

echo Starting SkyBlink Backend on http://localhost:8000 ...
start "SkyBlink Backend (8000)" cmd /k "cd /d ""%~dp0backend"" && .venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000"

echo Starting SkyBlink Frontend on http://localhost:3000 ...
start "SkyBlink Frontend (3000)" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"

echo.
echo ========================================================
echo   SkyBlink is starting!
echo   Frontend:   http://localhost:3000
echo   Backend:    http://localhost:8000/api/health
echo   Check HTML: %~dp0check.html
echo   CLI:        skyblink-cli.bat --help
echo ========================================================
echo.
pause
