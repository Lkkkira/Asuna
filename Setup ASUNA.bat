@echo off
cd /d "%~dp0"
python setup_assistant.py
if errorlevel 1 echo Setup did not finish. Check the message above.
pause
