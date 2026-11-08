@echo off
cd /d "%~dp0"
python voice_setup.py
if errorlevel 1 (
    echo Voice setup did not finish. Check the message above and retry.
)
pause
