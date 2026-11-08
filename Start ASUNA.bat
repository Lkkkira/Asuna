@echo off
cd /d "%~dp0"
if exist ".venv-voice\Scripts\python.exe" (
    ".venv-voice\Scripts\python.exe" asuna.py
) else (
    python asuna.py
)
if errorlevel 1 pause
