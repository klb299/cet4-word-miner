@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul
if %errorlevel%==0 (
  python run.py %*
) else (
  echo 没有找到 python，请先安装 Python 3 并勾选 Add to PATH
)
pause
