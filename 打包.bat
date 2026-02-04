@echo off
chcp 65001 >nul
cls

echo ========================================
echo   AutoFlow v1.2.0 - 專業打包腳本
echo ========================================
echo.

cd /d "%~dp0main"

echo [1/6] 檢查 Python 環境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 未安裝 Python，請前往官網安裝。
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VER=%%i
echo [OK] Python %PYTHON_VER%
echo.

echo [2/6] 安裝/更新必要組件...
echo   - 更新 pip...
python -m pip install --upgrade pip --quiet
echo   - 安裝依賴套件...
python -m pip install -r ../requirements.txt --quiet
echo   - 安裝 PyInstaller...
python -m pip install pyinstaller --quiet
if errorlevel 1 (
    echo [錯誤] 依賴套件安裝失敗
    pause
    exit /b 1
)
echo [OK] 所有組件已就緒
echo.

echo [3/6] 準備打包資源...
set ICON_PATH=pic\umi_粉紅色.ico

:: 檢查圖示是否存在
if not exist "%ICON_PATH%" (
    echo [警告] 找不到圖示檔案: %ICON_PATH%
    echo 將使用默認圖示打包
    set ICON_PARAM=
) else (
    echo [OK] 圖示檔案: %ICON_PATH%
    set ICON_PARAM=--icon="%ICON_PATH%"
)

:: 檢查版本資訊檔案
if not exist "version_info.txt" (
    echo [警告] 找不到 version_info.txt
    set VERSION_PARAM=
) else (
    echo [OK] 版本資訊: version_info.txt
    set VERSION_PARAM=--version-file=version_info.txt
)
echo.

echo [4/6] 執行打包程序 (PyInstaller)...
echo   這可能需要幾分鐘，請稍候...
echo.

:: 執行打包命令
pyinstaller --name="AutoFlow" ^
    --onefile ^
    --windowed ^
    %ICON_PARAM% ^
    %VERSION_PARAM% ^
    --add-data="version_manager.py;." ^
    --add-data="version_info_dialog.py;." ^
    --add-data="multi_player.py;." ^
    --add-data="video_list_item_new.py;." ^
    --add-data="about.py;." ^
    --add-data="pic;pic" ^
    --add-data="TTF;TTF" ^
    --hidden-import=PyQt6.QtCore ^
    --hidden-import=PyQt6.QtGui ^
    --hidden-import=PyQt6.QtWidgets ^
    --hidden-import=PyQt6.QtMultimedia ^
    --hidden-import=PyQt6.QtMultimediaWidgets ^
    --hidden-import=requests ^
    --clean ^
    --noconfirm ^
    ChroLens_AutoFlow.py

if errorlevel 1 (
    echo.
    echo [錯誤] 打包過程發生異常
    pause
    exit /b 1
)

echo.
echo [5/6] 清理暫存檔案...
if exist build (
    rmdir /s /q build
    echo   - 已刪除 build 資料夾
)
if exist AutoFlow.spec (
    del /q AutoFlow.spec
    echo   - 已刪除 AutoFlow.spec
)
if exist __pycache__ (
    rmdir /s /q __pycache__
    echo   - 已刪除 __pycache__
)
echo.

echo [6/6] 驗證輸出檔案...
if exist "dist\AutoFlow.exe" (
    for %%A in ("dist\AutoFlow.exe") do set SIZE=%%~zA
    echo [OK] AutoFlow.exe (大小: %SIZE% bytes)
) else (
    echo [錯誤] 找不到輸出檔案
    pause
    exit /b 1
)

echo.
echo ========================================
echo   ✨ 打包成功完成！ ✨
echo ========================================
echo.
echo 執行檔位置: %~dp0main\dist\AutoFlow.exe
echo 檔案大小: %SIZE% bytes
echo.
echo 功能包含:
echo   ✓ 女優名稱搜尋 (JavBus)
echo   ✓ 廠商分類備用方案
echo   ✓ FC2 自動分類
echo   ✓ 子資料夾支援
echo   ✓ 多窗瀏覽功能
echo   ✓ 自動更新檢查
echo.
echo 按任意鍵開啟輸出資料夾...
pause >nul

explorer "%~dp0main\dist"

