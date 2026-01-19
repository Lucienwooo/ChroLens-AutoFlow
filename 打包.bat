@echo off
chcp 65001 >nul
echo ========================================
echo   AutoFlow (ChroLens) - 專業打包腳本
echo ========================================
echo.

cd /d "%~dp0main"

echo [1/5] 檢查 Python 環境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 未安裝 Python，請前往官網安裝。
    pause
    exit /b 1
)
echo [OK] Python 環境正常
echo.

echo [2/5] 安裝/更新 必要組件...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r ../requirements.txt
python -m pip install pyinstaller
if errorlevel 1 (
    echo [錯誤] 依賴套件安裝失敗
    pause
    exit /b 1
)
echo.

echo [3/5] 執行打包程序 (PyInstaller)...
set ICON_PATH=pic\umi_粉紅色.ico

:: 檢查圖示是否存在
if not exist "%ICON_PATH%" (
    echo [警告] 找不到圖示檔案: %ICON_PATH%
    echo 將使用默認圖示打包
    set ICON_PARAM=
) else (
    set ICON_PARAM=--icon="%ICON_PATH%"
)

:: 執行打包命令
:: --add-data 格式: "源路徑;目標資料夾"
pyinstaller --name="AutoFlow" ^
    --onefile ^
    --windowed ^
    %ICON_PARAM% ^
    --version-file=version_info.txt ^
    --add-data="version_manager.py;." ^
    --add-data="version_info_dialog.py;." ^
    --add-data="multi_player.py;." ^
    --add-data="about.py;." ^
    --add-data="pic;pic" ^
    --add-data="TTF;TTF" ^
    --clean ^
    ChroLens_AutoFlow.py

if errorlevel 1 (
    echo [錯誤] 打包過程發生異常
    pause
    exit /b 1
)

echo.
echo [4/5] 清理冗餘暫存...
if exist build rmdir /s /q build
if exist AutoFlow.spec del /q AutoFlow.spec

echo.
echo ========================================
echo   ✨ 打包成功完成！ ✨
echo ========================================
echo.
echo 執行檔位置: %~dp0main\dist\AutoFlow.exe
echo.
echo 按任意鍵開啟輸出資料夾...
pause >nul

explorer "%~dp0main\dist"
