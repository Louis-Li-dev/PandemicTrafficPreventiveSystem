# 疫情與交通多層級預警拓樸分析系統 (Pandemic & Traffic Preventive System)

## 📌 系統簡介
本系統是一個學術級的多層級傳播鏈拓樸分析與預警系統，基於 Python Flask、Pandas、PyArrow 以及 Scikit-Learn 的機器學習分群演算法（如 Agglomerative Clustering、HDBSCAN）構建。系統核心功能在於對城市級別的移動數據進行全域 (Global Hubs) 與區域 (Local Hubs) 的拓樸網絡分析，並藉此模擬傳播鏈擴散（包括第一層直接接觸 Primary 與第二層間接接觸 Secondary 受影響人次），進一步提供個人軌跡防禦預警與交通阻斷影響分析。

---

## 🚀 核心功能特色

### 1. 🗂️ 多資料集極速自適應載入 (A、B、C、D)
* 系統無縫支援 `City A`、`City B`、`City C`、`City D` 等多個不同規模的城市數據集。
* **PyArrow 串流過濾技術**：針對包含 **1.11 億行** 數據的 City A，系統採用極輕量的 UID 先行預讀並以 PyArrow 快取過濾載入，徹底解決傳統 `read_parquet` 面臨的記憶體溢出 (OutOfMemory) 崩潰問題，載入時間從數分鐘壓縮至 **1.3 秒**。
* **自適應 UID 分布**：智慧識別各城市資料集之獨特 UID 範圍（例如 City A `0~99999`，City B `27001~30000`），動態精確篩選使用者。

### 2. 📊 全域與局域 Hubs 拓樸網絡圖繪製
* 基於使用者歷史移動軌跡進行空間時序滾動中位數去噪 (Smoothing Window)。
* 利用空間密度聚類法自動提煉出使用者的個人區域 Hub，再匯聚為全城市之全域 Hubs (Global Hubs) 拓樸圖，並支援網頁即時統計分析。

### 3. 🕸️ 傳播鏈連鎖影響追蹤 (Cascade Tracer)
* **雙重模式分析**：支援**路徑整合 (Path-Integrated)** 與**僅 Hub 模式 (Hub-Only)** 分析，以動態傳播樹圖表呈現。
* **視覺化標註**：地圖上以 **黑色星形** 標註事件源頭 Hub，**紅底方塊** 代表第一層 (Primary) 接觸，**黃底方塊** 代表第二層 (Secondary) 接觸。
* **匯出預測報告**：支援一鍵匯出預測結果為學術與政策研究級的 CSV 報表。

### 4. 🚨 個人軌跡風險預警系統 (Tab 3)
* 允許使用者動態輸入任意時間區間與坐標的移動足跡。
* 支援**多事故 Hub** 同時假設，自動計算使用者與任一事故源頭 Hub 的最近物理距離。
* **接觸時間追蹤與預警**：系統不只提出警告，更會在右側貼心呈現 **「事件日受影響名單與接觸時間表」**，將當天被波及的 Primary 與 Secondary 使用者與其接觸時間（如 `12:30`）分門別類完整列出。

### 5. 🚧 交通建設阻斷分析 (Tab 4)
* 針對重要交通節點（Global Hub）發生阻斷或堵塞時，模擬在特定天數與時間區間內，直接或間接造成路網癱瘓與使用者路徑中斷的阻礙人數與時間分布趨勢。

---

## 🛠️ 技術棧
* **後端架構**：Python 3.8+ / Flask / Flask-CORS
* **科學計算 & 機器學習**：Pandas / PyArrow / NumPy / Scikit-Learn (AgglomerativeClustering)
* **資料視覺化**：Matplotlib (後端即時渲染並以 Base64 格式輸出前端) / Chart.js
* **前端介面**：HTML5 Semantic tags / Vanilla CSS3 (具玻璃擬物 Glassmorphism 質感與深色側邊欄) / Vanilla ES6 JavaScript

---

## 📁 專案結構
```text
TGIS/
├── data/                    # 存放城市 Parquet 數據集 (A, B, C, D)
├── templates/
│   └── index.html           # 前端主介面網頁模板
├── static/
│   ├── main.js              # 前端控制與 API 交互邏輯
│   └── style.css            # 精美擬真儀表板樣式
├── app.py                   # 後端 Flask API 控制中心 (多資料集自適應載入與預警邏輯)
├── tracer.py                # 核心演算法 (多層級傳播樹、Hub 拓樸計算模組)
├── requirements.txt         # 系統依賴軟體套件清單
└── README.md                # 本文件說明檔
```

---

## 💻 快速安裝與運行指南

### 步驟 1. 下載並複製專案
確保您已將本專案複製至您的本地 Windows 電腦工作目錄中：
```bash
git clone https://github.com/Louis-Li-dev/PandemicTrafficPreventiveSystem.git
cd TGIS
```

### 步驟 2. 安裝必要 Python 依賴
建議在專屬虛擬環境 (Virtualenv / Conda) 中運行，安裝專案所需依賴軟體：
```bash
pip install -r requirements.txt
```

### 步驟 3. 啟動伺服器
執行主程式啟動 Flask 後端：
```bash
python app.py
```
若啟動成功，您會看見：
```text
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

### 步驟 4. 開始使用
打開您的瀏覽器，造訪 `http://127.0.0.1:5000`：
1. 右上角將亮起綠色指示燈 **`🟢 伺服器已連線 (請點擊「建立全域 Hubs」)`**。
2. 自由切換您想載入的 Parquet 資料集並點擊 **「建立全域 Hubs」**，系統將以極速完成初始化！
3. 您可以自由切換「追蹤結果分析」、「個人預警系統」或「交通影響分析」分頁，探索所有完整的數據洞察。
