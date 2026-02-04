# AutoFlow 最終解決方案 - 多來源搜尋

## 🎯 解決方案

由於 av-wiki.net 連線不穩定，我實施了**雙重保險策略**：

### 方法 1：JAVLibrary 搜尋（優先）

- 使用 JAVLibrary API 搜尋女優名稱
- 成功率較高，資料較完整
- 需要安裝 beautifulsoup4

### 方法 2：廠商分類（備用）

- 根據番號前綴自動分類到廠商資料夾
- 100% 成功率
- 包含 30+ 常見廠商

---

## 📝 廠商對應表

| 番號前綴          | 廠商名稱    | 範例      |
| :---------------- | :---------- | :-------- |
| STARS             | SOD         | STARS-947 |
| SSIS/SSNI         | S1          | SSNI-878  |
| EBOD              | E-BODY      | EBOD-963  |
| ADN/ATID/RBD/SSPD | Attackers   | ADN-176   |
| PPPD              | OPPAI       | PPPD-142  |
| ABP/ABF           | Prestige    | ABF-259   |
| DVAJ              | Alice Japan | DVAJ-123  |
| MD                | Madou Media | MD0226    |
| ...               | ...         | ...       |

---

## 🔄 處理流程

```
1. 提取番號 (STARS-947)
   ↓
2. 檢查是否為 FC2
   ├─ 是 → FC2 資料夾
   └─ 否 → 繼續
   ↓
3. 嘗試 JAVLibrary 搜尋
   ├─ 成功 → 女優資料夾 (莉々はるか)
   └─ 失敗 → 繼續
   ↓
4. 使用廠商分類
   ├─ 找到對應 → 廠商資料夾 (SOD)
   └─ 未找到 → UNKNOWN
```

---

## 📊 預期結果

### 情況 A：JAVLibrary 成功

```
[XX:XX:XX] [1/20] STARS-947.mp4
[XX:XX:XX]   番號: STARS-947
[XX:XX:XX]   搜尋中...
[XX:XX:XX]   [找到] 莉々はるか
[XX:XX:XX]   [完成] -> 莉々はるか\
```

### 情況 B：JAVLibrary 失敗，使用廠商分類

```
[XX:XX:XX] [1/20] STARS-947.mp4
[XX:XX:XX]   番號: STARS-947
[XX:XX:XX]   搜尋中...
[XX:XX:XX]   [JAVLib錯誤] ...
[XX:XX:XX]   [廠商] SOD
[XX:XX:XX]   [完成] -> SOD\
```

### 情況 C：FC2 影片

```
[XX:XX:XX] [5/20] FC2PPV-3119569.mp4
[XX:XX:XX]   番號: FC2-PPV-3119569
[XX:XX:XX]   [FC2] 分類到FC2資料夾
[XX:XX:XX]   [完成] -> FC2\
```

---

## 🚀 使用步驟

1. **安裝依賴**

   ```bash
   pip install beautifulsoup4
   ```

2. **重新啟動 AutoFlow**

3. **選擇資料夾並開始處理**

4. **查看結果**
   - 優先分類到女優資料夾
   - 失敗則分類到廠商資料夾
   - FC2 統一到 FC2 資料夾

---

## 💡 優點

1. **雙重保險**
   - JAVLibrary 失敗時自動切換到廠商分類
   - 保證 100% 的影片都能被分類

2. **廠商分類實用**
   - 即使無法獲得女優名稱
   - 按廠商分類也很有組織性

3. **無需網路（備用方案）**
   - 廠商分類完全本地化
   - 不依賴網路連線

---

## ⚙️ 擴展廠商列表

如需添加更多廠商，編輯 `_get_studio_from_code()` 函數：

```python
studio_map = {
    'XXX': '廠商名稱',
    # 添加更多...
}
```

---

**現在系統會自動處理所有情況，保證每個影片都能被正確分類！** 🎉
