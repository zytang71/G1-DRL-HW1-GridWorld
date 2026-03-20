# GridWorld (Flask) - 1-1 / 1-2 / 1-3

此專案為強化學習作業的 GridWorld 視覺化與互動系統，使用 Flask + 原生 HTML/CSS/JavaScript 開發。

## 功能總覽

### 1-1 網格地圖開發
- 使用者可設定網格大小 `n`，範圍 `5 ~ 9`。
- 可用滑鼠點擊設定：
  - 起點（綠色）
  - 終點（紅色）
  - 障礙物（灰色）
- 障礙物限制：**最多 `n-2` 個**（不是一定要剛好 `n-2`）。

### 1-2 策略顯示與價值評估
- 可產生每個狀態的隨機策略（`↑ ↓ ← →`）。
- 固定策略下執行 Iterative Policy Evaluation，求 `V(s)`。
- 1-2 固定獎勵：
  - 每步 `-1`
  - 進入終點 `0`
- 可調參數：
  - `gamma`
  - `theta`
  - `max iterations`

### 1-3 訓練（Policy Iteration）
- 以上一步策略為初始策略。
- 執行「策略評估 + 策略改進」直到收斂或達上限。
- 可調參數：
  - `step reward`
  - `goal reward`
  - `gamma`
  - `theta`
  - `max eval iterations`
  - `max policy iterations`
- 訓練後會回傳並顯示：
  - 收斂後策略
  - `V(s)`
  - 最佳路徑（由起點依策略追蹤到終點）
- 最佳路徑支援動畫與重播。

## UI 操作流程
1. 輸入 `n` 並按「建立網格」。
2. 透過點擊模式設定起點、終點、障礙物。
3. 按「產生隨機策略（1-2）」。
4. 可先按「策略評估（1-2）」查看 `V(s)`。
5. 按「開始訓練（1-3）」執行訓練。
6. 使用「重播路徑動畫」反覆觀看最佳路徑。
7. 使用「重設參數」回到預設值。

## 環境需求
- Python 3.10+（實測可用 3.13）
- Flask 3.x

## 安裝與啟動

### 一般 Python
```powershell
pip install -r requirements.txt
python app.py
```

### Conda（你目前使用的環境）
```powershell
conda activate DRL
pip install -r requirements.txt
python app.py
```

啟動後開啟：
- `http://127.0.0.1:5000`

## API 一覽

### `POST /api/validate-grid`
檢查地圖資料是否合法。

### `POST /api/generate-policy`
輸入地圖，回傳隨機策略。

### `POST /api/evaluate-policy`
輸入地圖 + 策略 + `gamma/theta/max_iterations`，回傳 `V(s)`（固定 1-2 獎勵）。

### `POST /api/train-policy`
輸入地圖 + 初始策略 + 1-3 參數，回傳：
- 訓練後策略
- `V(s)`
- `best_path`
- `reached_goal`
- 迭代統計資訊

## 專案結構
```text
.
├─ app.py
├─ requirements.txt
├─ 1-2-policy-evaluation-method.md
├─ 1-3-training-method.md
├─ templates/
│  └─ index.html
└─ static/
   ├─ app.js
   └─ style.css
```

## 備註
- 終點視為 terminal state。
- 動作若撞牆或撞障礙物，代理人會留在原地。
- 若策略無法到達終點（例如循環），`reached_goal` 會回傳 `false`。
