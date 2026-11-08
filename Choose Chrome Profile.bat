@echo off
cd /d "%~dp0"
if exist ".venv-voice\Scripts\python.exe" (
    ".venv-voice\Scripts\python.exe" browser_profile.py
) else (
    python browser_profile.py
)
pause
