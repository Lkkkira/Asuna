@echo off
cd /d "%~dp0"
if exist ".venv-voice\Scripts\python.exe" (
    ".venv-voice\Scripts\python.exe" diagnostics.py
) else (
    python diagnostics.py
)
pause
