# AutoFlow 番號提取修復總結

## 📊 Token 使用狀況

**已使用：166,271 / 200,000 tokens (83%)**
**剩餘：33,729 tokens**

---

## ✅ 已完成的修復

### 問題：番號提取邏輯優化

**原問題：**

1. 所有影片都被標記為 `UNKNOWN` 並跳過
2. FC2 影片番號提取錯誤（`PPV-XXX` 而非 `FC2-PPV-XXX`）
3. 番號提取不夠精確

**修復內容：**

#### 1. 優化番號提取邏輯

```python
def extract_video_code(self, filename):
    """提取影片番號"""
    name = Path(filename).stem

    # 移除常見前綴
    name = re.sub(r'^(A-)?MOSAIC-ARCHIVE-', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^ARCHIVE-MOSAIC-', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^ARCHIVE-', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^MOSAIC-', '', name, flags=re.IGNORECASE)

    # 搜尋模式（使用 \b 確保匹配完整單詞）
    patterns = [
        r'\bFC2-?PPV-?\d+\b',        # FC2PPV-3119569
        r'\b[A-Z]{2,}-\d{2,4}\b',    # EBWH-179, STARS-947, ABF-259
        r'\b[A-Z]+\d{3,}\b',         # MD0226
    ]

    for pattern in patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            code = match.group(0).upper()
            # 統一 FC2 格式
            if 'FC2' in code:
                code = re.sub(r'FC2-?PPV-?', 'FC2-PPV-', code, flags=re.IGNORECASE)
            return code

    return None
```

#### 2. 清理快取中的無效條目

```python
def load_cache(self):
    """載入快取"""
    cache_file = Path.home() / "Downloads" / "actress_cache.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                self.cache = json.load(f)
                # 過濾掉無效的快取條目
                self.cache = {k: v for k, v in self.cache.items()
                             if v not in ["如果系統沒有", "UNKNOWN", "MULTIPLE"]}
            self.add_log(f"已載入快取: {len(self.cache)} 個條目")
        except Exception as e:
            print(f"快取載入失敗: {e}")
```

---

## 🎯 測試結果

### 番號提取測試（全部通過 ✓）

| 檔案名稱                     | 預期番號        | 提取結果        | 狀態 |
| :--------------------------- | :-------------- | :-------------- | :--: |
| MOSAIC-ARCHIVE-ebwh-179.mp4  | EBWH-179        | EBWH-179        |  ✓   |
| STARS-947.mp4                | STARS-947       | STARS-947       |  ✓   |
| ARCHIVE-MOSAIC-ABF-259.mp4   | ABF-259         | ABF-259         |  ✓   |
| A-MOSAIC-ARCHIVE-adn-176.mp4 | ADN-176         | ADN-176         |  ✓   |
| ARCHIVE-FC2PPV-3119569.mp4   | FC2-PPV-3119569 | FC2-PPV-3119569 |  ✓   |
| FC2PPV-3292343-1.mp4         | FC2-PPV-3292343 | FC2-PPV-3292343 |  ✓   |
| fc2ppv-33632.mp4             | FC2-PPV-33632   | FC2-PPV-33632   |  ✓   |
| MD0226 紗花嫁 張芸熙.mp4     | MD0226          | MD0226          |  ✓   |
| MOSAIC-ARCHIVE-pppd-142.mp4  | PPPD-142        | PPPD-142        |  ✓   |
| MOSAIC-ARCHIVE-pppd-804.mp4  | PPPD-804        | PPPD-804        |  ✓   |

---

## 🔧 關鍵改進

### 1. 使用單詞邊界 (`\b`)

- 確保匹配完整的番號，不會誤匹配部分字串
- 避免 `EBWH-179` 被誤匹配為 `EBWH-1420226`

### 2. 限制數字長度

- 標準番號：`\d{2,4}` (2-4位數字)
- 簡單番號：`\d{3,}` (至少3位數字)
- 避免匹配到過長的數字串

### 3. FC2 格式統一

- 自動將 `FC2PPV-XXX`, `FC2-PPV-XXX`, `fc2ppv-XXX` 統一為 `FC2-PPV-XXX`
- 確保快取和搜尋的一致性

### 4. 清理無效快取

- 過濾掉 `UNKNOWN`, `MULTIPLE`, `如果系統沒有` 等無效條目
- 避免重複搜尋已知無法找到的番號

---

## 📝 使用範例

### 處理流程

```
1. 檔案: MOSAIC-ARCHIVE-ebwh-179.mp4
   ↓
2. 移除前綴: ebwh-179
   ↓
3. 提取番號: EBWH-179
   ↓
4. 搜尋網站: https://av-wiki.net/EBWH-179
   ↓
5. 提取女優名稱
   ↓
6. 建立資料夾並移動檔案
```

### 預期日誌

```
[20:XX:XX] [1/18] MOSAIC-ARCHIVE-ebwh-179.mp4
[20:XX:XX]   番號: EBWH-179
[20:XX:XX]   搜尋中...
[20:XX:XX]   [找到] 天月あず
[20:XX:XX]   [完成] -> 天月あず\
```

---

## ⚠️ 注意事項

1. **快取清理**
   - 如果之前有大量 `UNKNOWN` 快取，建議刪除快取檔案重新開始
   - 快取位置：`%USERPROFILE%\Downloads\actress_cache.json`

2. **網站搜尋**
   - 依賴 av-wiki.net 的可用性
   - 建議設定適當的延遲避免被封鎖

3. **女優名稱提取**
   - 依賴網站 title 格式：`番號 女優名稱 - 標題`
   - 如果格式改變可能需要調整解析邏輯

---

## 🚀 下一步測試

1. **刪除舊快取**

   ```
   刪除: %USERPROFILE%\Downloads\actress_cache.json
   ```

2. **重新執行處理**
   - 選擇資料夾
   - 點擊「開始」
   - 觀察日誌確認番號提取正確

3. **確認結果**
   - 檢查建立的資料夾是否為女優名稱
   - 確認影片已正確移動

---

**修復完成！準備測試！** 🎉
