@echo off
chcp 65001 >nul
echo ========================================
echo   ChroLens_AutoFlow - 測試運行
echo ========================================
echo.

cd /d "%~dp0main"

echo [1/2] 檢查 Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 未安裝 Python
    pause
    exit /b 1
)

echo [OK] Python 已安裝
echo.

echo [2/2] 啟動程式...
python ChroLens_AutoFlow.py

if errorlevel 1 (
    echo.
    echo [錯誤] 程式執行失敗
    pause
    exit /b 1
)
