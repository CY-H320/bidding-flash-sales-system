# 負載測試使用指南

## 快速開始

### 1. 安裝依賴

```powershell
pip install -r requirements.txt
```

### 2. 運行測試

```powershell
.\run_test.ps1
```

或指定參數：

```powershell
.\run_test.ps1 http://your-host 100 10 5m
# 參數: host users spawn-rate duration
```

### 3. 分析結果

測試完成後，會在 `results_<timestamp>/` 目錄下生成：
- `bid_requests.csv` - 每個 bid 請求的詳細記錄
- `results_stats.csv` - Locust 統計數據
- `report.html` - Locust HTML 報告

### 4. 生成視覺化圖表

```powershell
python analyze_bid_logs.py results_20231211_120000
```

會在 `results_<timestamp>/analysis/` 生成以下圖表：

1. **requests_per_second.png** - 每秒請求數折線圖
   - 顯示測試期間每秒的 bid 請求數量
   - 包含平均值和最大值標註

2. **bid_price_over_time.png** - Bid 價格隨時間變化圖
   - 顯示 bid 價格如何隨時間增長
   - 包含趨勢線（每秒增長率）

3. **success_rate_over_time.png** - 成功率隨時間變化圖
   - 每 5 秒統計的成功率
   - 幫助識別系統壓力下的表現

4. **response_time_distribution.png** - 響應時間分佈圖
   - 直方圖和箱型圖
   - 包含中位數、P95、P99 標註

5. **dashboard.png** - 綜合儀表板
   - 包含所有關鍵指標的單一視圖
   - 附帶測試摘要統計

## 測試特性

### Bid 價格隨時間增長

- **增長率**: $0.5/秒
- **基礎價格**: Session 的 base_price
- **隨機變動**: ±$20
- **範例**: 5 分鐘測試從 $100 增長到約 $250

### 詳細日誌記錄

每個 bid 請求都會記錄到 `bid_requests.csv`：

```csv
timestamp,elapsed_seconds,bid_price,success,response_time_ms
2023-12-11T12:00:01.234567,1.23,105.67,True,45.23
2023-12-11T12:00:02.456789,2.46,110.34,True,52.11
...
```

欄位說明：
- `timestamp`: ISO 格式的請求時間
- `elapsed_seconds`: 測試開始後的經過時間（秒）
- `bid_price`: 出價金額
- `success`: 請求是否成功（True/False）
- `response_time_ms`: 響應時間（毫秒）

### 數據分析能力

使用這些日誌，您可以：

1. **繪製每秒請求數**
   ```python
   import pandas as pd
   df = pd.read_csv('bid_requests.csv')
   df['second'] = df['elapsed_seconds'].round(0)
   requests_per_sec = df.groupby('second').size()
   ```

2. **分析價格趨勢**
   ```python
   import matplotlib.pyplot as plt
   plt.scatter(df['elapsed_seconds'], df['bid_price'])
   ```

3. **計算成功率**
   ```python
   success_rate = df['success'].mean() * 100
   ```

4. **分析響應時間**
   ```python
   print(f"Median: {df['response_time_ms'].median():.1f}ms")
   print(f"P95: {df['response_time_ms'].quantile(0.95):.1f}ms")
   ```

## 範例工作流程

```powershell
# 1. 運行測試 (100 用戶, 5 分鐘)
.\run_test.ps1 http://your-host 100 10 5m

# 2. 等待測試完成
# 測試結果自動保存到 results_<timestamp>/

# 3. 分析最新的測試結果
$latest = Get-ChildItem -Directory -Filter "results_*" | Sort-Object Name -Descending | Select-Object -First 1
python analyze_bid_logs.py $latest.Name

# 4. 查看圖表
explorer "$latest\analysis"

# 5. 打開 HTML 報告
explorer "$latest\report.html"
```

## 自定義調整

### 修改價格增長率

在 `locustfile.py` 中修改：

```python
time_factor = 0.5  # 改為其他值，如 1.0 表示每秒增加 $1
```

### 修改隨機變動範圍

```python
random_variance = random.uniform(0, 20)  # 改為 (0, 50) 增加變動範圍
```

### 調整統計區間

在 `analyze_bid_logs.py` 中修改成功率統計區間：

```python
df['interval'] = (df['elapsed_seconds'] // 5 * 5).astype(int)  # 改為 // 10 使用 10 秒區間
```

## 疑難排解

### 問題：CSV 文件為空

**原因**: 測試時間太短或沒有成功的請求

**解決方案**: 
- 延長測試時間
- 檢查伺服器是否正常運行
- 確認 session 已創建且未過期

### 問題：圖表生成失敗

**原因**: 缺少 matplotlib 或 pandas

**解決方案**:
```powershell
pip install pandas matplotlib numpy
```

### 問題：結果目錄名稱不匹配

**原因**: 腳本和日誌使用不同的時間戳

**解決方案**: 
確保使用測試生成的實際目錄名稱：
```powershell
Get-ChildItem -Directory -Filter "results_*"
```

## 進階用法

### 比較多次測試結果

```powershell
# 分析所有測試結果
Get-ChildItem -Directory -Filter "results_*" | ForEach-Object {
    Write-Host "Analyzing $($_.Name)..."
    python analyze_bid_logs.py $_.Name
}
```

### 導出統計摘要

```python
import pandas as pd
import glob

results = []
for dir in glob.glob("results_*/bid_requests.csv"):
    df = pd.read_csv(dir)
    df['second'] = df['elapsed_seconds'].round(0)
    rps = df.groupby('second').size()
    
    results.append({
        'test': dir,
        'total_requests': len(df),
        'duration': df['elapsed_seconds'].max(),
        'avg_rps': rps.mean(),
        'max_rps': rps.max(),
        'success_rate': df['success'].mean() * 100,
        'median_response': df['response_time_ms'].median()
    })

summary = pd.DataFrame(results)
summary.to_csv('test_summary.csv', index=False)
print(summary)
```
