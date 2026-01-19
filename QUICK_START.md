# 🚀 ChroLens_AutoFlow 快速開始指南

## 📦 專案結構

```
ChroLens_AutoFlow/
├── main/                           # 主程式目錄
│   ├── ChroLens_AutoFlow.py       # 主程式 (1000+ 行)
│   ├── version_manager.py         # 版本管理器
│   ├── about.py                   # 關於對話框
│   ├── version_info.txt           # 版本資訊 (PyInstaller)
│   └── create_icon.py             # 圖示生成腳本
├── requirements.txt               # Python 依賴套件
├── 打包.bat                       # 一鍵打包腳本
├── 測試運行.bat                   # 測試運行腳本
├── LICENSE                        # GPL v3 + Commercial
├── README.md                      # 專案說明
└── UPDATE_LOG.md                  # 更新日誌
```

## ⚡ 立即開始

### 方法 1: 測試運行 (開發)

```bash
# 1. 進入專案目錄
cd ChroLens_AutoFlow

# 2. 執行測試腳本
測試運行.bat
```

### 方法 2: 打包成 .exe

```bash
# 1. 執行打包腳本
打包.bat

# 2. 等待完成 (約 2-3 分鐘)

# 3. 執行檔位置
main\dist\ChroLens_AutoFlow.exe
```

## 🎯 核心功能

### 1. 自動搜尋女優

- 使用 av-wiki.net API
- 智能番號提取
- 快取機制避免重複搜尋

### 2. 影片縮圖預覽

- OpenCV 自動提取第 5 秒畫面
- 320x180 高清縮圖
- 點擊開啟影片

### 3. 批次處理

- 一次處理大量影片
- 即時進度顯示
- 自動分類到女優資料夾

### 4. 版本更新

- 自動檢查 GitHub Releases
- 一鍵下載更新
- 自動安裝並重啟

## 🎨 UI 特色

### 深色主題 (預設)

- 背景: `#1C1C1E`
- 卡片: `#2C2C2E`
- 文字: `#E5E5EA`

### 淺色主題

- 背景: `#F5F5F7`
- 卡片: `#FFFFFF`
- 文字: `#1C1C1E`

### 佈局

- **左側 (450px)**: 控制面板
- **右側 (彈性)**: 影片列表

## 📋 依賴套件

```
PyQt6>=6.6.0          # GUI 框架
requests>=2.31.0      # HTTP 請求
opencv-python>=4.8.0  # 影片處理
numpy>=1.24.0         # 數值計算
packaging>=23.0       # 版本比較
Pillow>=10.0.0        # 圖片處理
```

## 🔧 版本管理

### 版本號格式

- `主版本.次版本.修訂版本`
- 例如: `1.0.0`

### 更新機制

1. 啟動時自動檢查更新
2. 發現新版本顯示對話框
3. 下載 GitHub Release .zip
4. 解壓縮並應用更新
5. 自動重啟程式

### GitHub Release 要求

- Tag: `v1.0.0`
- Asset: `ChroLens_AutoFlow_v1.0.0.zip`
- 包含 `main/` 目錄和 `.exe`

## 🛠️ 開發指南

### 修改版本號

1. `main/ChroLens_AutoFlow.py` → `VERSION = "1.0.0"`
2. `main/version_info.txt` → `filevers=(1, 0, 0, 0)`

### 新增功能

1. 在 `main/ChroLens_AutoFlow.py` 中修改
2. 測試運行確認功能
3. 更新 `UPDATE_LOG.md`
4. 打包並測試 .exe

### 發布新版本

1. 更新版本號
2. 更新 `UPDATE_LOG.md`
3. 打包成 .exe
4. 創建 GitHub Release
5. 上傳 .zip 檔案

## 📊 統計資訊

- **主程式**: ~1000 行
- **版本管理器**: ~200 行
- **關於對話框**: ~100 行
- **總計**: ~1300 行 Python 程式碼

## 🎉 完成!

您現在有一個完整的 ChroLens 系列應用程式!

### 特色:

✅ 參考 Mimic 的專案結構
✅ 完整的版本管理系統
✅ 自動更新功能
✅ 專業的 UI 設計
✅ 完整的文件

### 下一步:

1. 測試運行程式
2. 打包成 .exe
3. 創建 GitHub Repository
4. 發布第一個 Release

---

**Lucien** - ChroLens 系列
© 2026 All rights reserved.
