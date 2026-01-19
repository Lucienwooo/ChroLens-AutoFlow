# ChroLens_AutoFlow

🎬 **智能影片自動分類工具** - ChroLens 系列

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/Lucienwooo/ChroLens_AutoFlow/releases)
[![License](https://img.shields.io/badge/license-GPL%20v3%20%2B%20Commercial-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

## 📖 簡介

ChroLens_AutoFlow 是一款智能影片自動分類工具,使用 AI 技術自動搜尋女優名稱並分類影片。

### ✨ 主要特色

- 🤖 **自動搜尋** - 使用 av-wiki.net 自動搜尋女優名稱
- 💾 **智能快取** - 避免重複搜尋,提升效率
- 🖼️ **縮圖預覽** - OpenCV 自動提取影片縮圖
- 📦 **批次處理** - 一次處理大量影片
- 🌙 **雙主題** - 深色/淺色主題切換
- 🔄 **自動更新** - 內建版本更新功能
- 📊 **即時統計** - 處理進度即時顯示

## 🚀 快速開始

### 方法 1: 下載執行檔 (推薦)

1. 前往 [Releases](https://github.com/Lucienwooo/ChroLens_AutoFlow/releases) 頁面
2. 下載最新版本的 `.zip` 檔案
3. 解壓縮後執行 `ChroLens_AutoFlow.exe`

### 方法 2: 從原始碼執行

```bash
# 1. 克隆專案
git clone https://github.com/Lucienwooo/ChroLens_AutoFlow.git
cd ChroLens_AutoFlow

# 2. 安裝依賴
pip install -r requirements.txt

# 3. 執行程式
cd main
python ChroLens_AutoFlow.py
```

## 📦 打包成執行檔

```bash
# 執行打包腳本
打包.bat

# 執行檔位置
main\dist\ChroLens_AutoFlow.exe
```

## 🎯 使用方式

1. **選擇資料夾** - 點擊「📁 選擇資料夾」選擇包含影片的資料夾
2. **查看列表** - 右側會顯示所有影片的縮圖預覽
3. **開始處理** - 點擊「▶️ 開始」自動搜尋並分類
4. **查看結果** - 影片會自動移動到對應的女優資料夾
5. **匯出資料** - 點擊「💾 匯出」匯出 CSV 檔案

## 📋 系統需求

- **作業系統**: Windows 10/11 (64-bit)
- **Python**: 3.10 或更高版本 (僅開發環境需要)
- **記憶體**: 建議 4GB 以上
- **硬碟空間**: 100MB 以上

## 🛠️ 技術棧

- **GUI 框架**: PyQt6
- **影片處理**: OpenCV
- **HTTP 請求**: requests
- **版本管理**: packaging
- **打包工具**: PyInstaller

## 📂 專案結構

```
ChroLens_AutoFlow/
├── main/
│   ├── ChroLens_AutoFlow.py    # 主程式
│   ├── version_manager.py      # 版本管理器
│   ├── about.py                # 關於對話框
│   └── version_info.txt        # 版本資訊
├── requirements.txt            # 依賴套件
├── 打包.bat                    # 打包腳本
├── LICENSE                     # 授權條款
└── README.md                   # 本文件
```

## 🔄 更新日誌

### v1.0.0 (2026-01-19)

- ✅ 初始版本發布
- ✅ 自動搜尋女優名稱
- ✅ 影片縮圖預覽
- ✅ 深色/淺色主題
- ✅ 自動更新功能

## 📄 授權條款

本專案採用雙重授權:

- **GPL v3** - 開源使用
- **Commercial** - 商業使用

詳見 [LICENSE](LICENSE) 檔案。

## 👨‍💻 作者

**Lucien**

- GitHub: [@Lucienwooo](https://github.com/Lucienwooo)

## 🙏 致謝

- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI 框架
- [OpenCV](https://opencv.org/) - 影片處理
- [av-wiki.net](https://av-wiki.net/) - 資料來源

## 📞 支援

如有問題或建議,請:

1. 提交 [Issue](https://github.com/Lucienwooo/ChroLens_AutoFlow/issues)
2. 發送 Pull Request
3. 聯繫作者

---

© 2026 Lucien. All rights reserved.
