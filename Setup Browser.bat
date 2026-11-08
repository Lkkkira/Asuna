@echo off
cd /d "%~dp0"
python browser_setup.py
if errorlevel 1 echo Browser setup did not finish. Check the message above.
pause
