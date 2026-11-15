@echo off
if not exist "%~dp0backend\.venv\Scripts\python.exe" (
    echo [ERROR] Python virtualenv not found at backend\.venv
    exit /b 1
)
"%~dp0backend\.venv\Scripts\python.exe" "%~dp0backend\cli.py" %*
