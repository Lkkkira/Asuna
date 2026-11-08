@echo off
cd /d "%~dp0"
if exist ".venv-voice\Scripts\python.exe" (
    ".venv-voice\Scripts\python.exe" restore_assistant.py
) else (
    python restore_assistant.py
)
