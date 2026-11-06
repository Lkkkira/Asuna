@echo off
cd /d "%~dp0"
python asuna.py
if errorlevel 1 pause
