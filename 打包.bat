@echo off
chcp 65001 >nul
echo ========================================
echo   ChroLens_AutoFlow - 打包腳本
echo ========================================
echo.

cd /d "%~dp0main"

echo [1/5] 檢查 Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 未安裝 Python
    echo.
    echo 請前往下載並安裝 Python 3.10+:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [OK] Python 已安裝
echo.

echo [2/5] 建立圖示...
cd /d "%~dp0"
if exist "main\create_icon.py" (
    python main\create_icon.py
) else (
    echo [警告] 圖示生成腳本不存在
)

echo.
echo [3/5] 安裝依賴套件...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt
python -m pip install pyinstaller

if errorlevel 1 (
    echo [錯誤] 套件安裝失敗
    pause
    exit /b 1
)

echo.
echo [4/5] 打包應用程式...
cd /d "%~dp0main"

if exist "icon.ico" (
    pyinstaller --name="ChroLens_AutoFlow" ^
        --onefile ^
        --windowed ^
        --icon=icon.ico ^
        --version-file=version_info.txt ^
        --add-data="version_manager.py;." ^
        --add-data="about.py;." ^
        --clean ^
        ChroLens_AutoFlow.py
) else (
    pyinstaller --name="ChroLens_AutoFlow" ^
        --onefile ^
        --windowed ^
        --version-file=version_info.txt ^
        --add-data="version_manager.py;." ^
        --add-data="about.py;." ^
        --clean ^
        ChroLens_AutoFlow.py
)

if errorlevel 1 (
    echo [錯誤] 打包失敗
    pause
    exit /b 1
)

echo.
echo [5/5] 清理暫存檔案...
if exist build rmdir /s /q build
if exist *.spec del /q *.spec

echo.
echo ========================================
echo   打包完成!
echo ========================================
echo.
echo 執行檔位置:
echo %~dp0main\dist\ChroLens_AutoFlow.exe
echo.
echo 按任意鍵開啟資料夾...
pause >nul

explorer "%~dp0main\dist"
