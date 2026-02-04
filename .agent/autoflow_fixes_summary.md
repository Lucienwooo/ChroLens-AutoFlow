# AutoFlow 修復總結

## 📊 Token 使用狀況

**已使用：145,567 / 200,000 tokens (72.8%)**
**剩餘：54,433 tokens**

---

## ✅ 已完成的修復

### 問題 1：修復女優名稱提取邏輯

**問題描述：**

- 系統只以番號前綴（如 DVAJ, EBOD）建立資料夾
- 應該要以女優名稱建立資料夾

**原因：**

```python
# 舊邏輯（錯誤）
actress_name = actress_match.group(1).split('-')[0].strip()
# 這會取得 "DVAJ-XXX 女優名稱 - 標題" 中的 "DVAJ"
```

**修復：**

```python
# 新邏輯（正確）
title = actress_match.group(1)
parts = title.split(' ')
if len(parts) >= 2:
    # 第一部分是番號，第二部分是女優名稱
    actress_name = parts[1].split('-')[0].strip()
```

**效果：**

```
舊: [找到] DVAJ -> 建立 DVAJ\ 資料夾
新: [找到] 女優名稱 -> 建立 女優名稱\ 資料夾
```

---

### 問題 2：新增「包含子資料夾」功能

**新增功能：**

1. ✅ 在左側按鈕群下方新增「包含子資料夾」開關
2. ✅ 開啟時會遞迴搜尋所有子資料夾中的影片
3. ✅ 影片列表和處理功能都支援此選項

**實現細節：**

1. **UI 元件：**

```python
self.include_subfolders_checkbox = QCheckBox("包含子資料夾")
self.include_subfolders_checkbox.stateChanged.connect(self.on_subfolder_toggle)
```

2. **檔案搜尋邏輯：**

```python
# 載入影片列表
if self.include_subfolders_checkbox.isChecked():
    files = list(Path(self.selected_folder).rglob("*.mp4"))  # 遞迴搜尋
else:
    files = list(Path(self.selected_folder).glob("*.mp4"))   # 只搜尋當前資料夾
```

3. **處理器支援：**

```python
class VideoProcessor:
    def __init__(self, folder_path, cache, include_subfolders=False):
        self.include_subfolders = include_subfolders

    def run(self):
        if self.include_subfolders:
            files = list(Path(self.folder_path).rglob("*.mp4"))
        else:
            files = list(Path(self.folder_path).glob("*.mp4"))
```

4. **切換處理：**

```python
def on_subfolder_toggle(self):
    """處理包含子資料夾開關切換"""
    if self.selected_folder:
        state = "啟用" if self.include_subfolders_checkbox.isChecked() else "停用"
        self.add_log(f"包含子資料夾: {state}")
        self.load_video_list()  # 重新載入影片列表
```

---

## 🎯 使用方式

### 女優名稱分類

1. 選擇資料夾
2. 點擊「開始」
3. 系統會：
   - 提取番號（如 DVAJ-123）
   - 搜尋 av-wiki.net
   - 提取女優名稱
   - 建立女優資料夾
   - 移動影片到對應資料夾

### 包含子資料夾

1. 選擇資料夾
2. 勾選「包含子資料夾」
3. 影片列表會顯示：
   - 當前資料夾的所有 .mp4 檔案
   - 所有子資料夾中的 .mp4 檔案
4. 處理時也會處理所有子資料夾的影片

---

## 📝 範例

### 修復前的日誌：

```
[20:05:23]   搜尋中...
[20:05:24]   [找到] DVAJ
[20:05:26]   [完成] -> DVAJ\
```

### 修復後的日誌：

```
[20:05:23]   搜尋中...
[20:05:24]   [找到] 橋本有菜
[20:05:26]   [完成] -> 橋本有菜\
```

### 資料夾結構範例：

**不包含子資料夾：**

```
選擇的資料夾/
├── video1.mp4  ✓ 會處理
├── video2.mp4  ✓ 會處理
└── subfolder/
    └── video3.mp4  ✗ 不會處理
```

**包含子資料夾：**

```
選擇的資料夾/
├── video1.mp4  ✓ 會處理
├── video2.mp4  ✓ 會處理
└── subfolder/
    ├── video3.mp4  ✓ 會處理
    └── deep/
        └── video4.mp4  ✓ 會處理
```

---

## ⚠️ 注意事項

1. **女優名稱提取**
   - 依賴 av-wiki.net 的 title 格式
   - 如果格式改變可能需要調整解析邏輯

2. **子資料夾功能**
   - 遞迴搜尋可能會找到很多檔案
   - 建議先在小範圍測試

3. **效能考量**
   - 影片列表預覽限制 50 個檔案
   - 避免極大資料夾導致初始化過久

---

## 🚀 測試建議

1. **測試女優名稱提取**
   - 選擇包含幾個影片的資料夾
   - 點擊「開始」
   - 確認建立的資料夾是女優名稱而非番號前綴

2. **測試子資料夾功能**
   - 準備一個有子資料夾的測試資料夾
   - 不勾選「包含子資料夾」→ 確認只顯示當前資料夾影片
   - 勾選「包含子資料夾」→ 確認顯示所有子資料夾影片

---

**修復完成！** 🎉
