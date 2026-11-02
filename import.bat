@echo off
chcp 65001 >nul
cd /d "%~dp0"
git pull --rebase
if "%~1"=="" (
  python scripts\ai_brain.py --push
) else (
  python scripts\ai_brain.py --file "%~1" --push
)
pause
