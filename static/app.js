const gridEl = document.getElementById("grid");
const nInput = document.getElementById("grid-size");
const buildGridBtn = document.getElementById("build-grid-btn");
const resetBtn = document.getElementById("reset-btn");
const validateBtn = document.getElementById("validate-btn");
const generatePolicyBtn = document.getElementById("generate-policy-btn");
const evaluatePolicyBtn = document.getElementById("evaluate-policy-btn");
const gammaInput = document.getElementById("gamma-input");
const thetaInput = document.getElementById("theta-input");
const maxIterInput = document.getElementById("max-iter-input");
const statusLine = document.getElementById("status-line");

const actionToArrow = {
  up: "↑",
  down: "↓",
  left: "←",
  right: "→",
};

const state = {
  n: 5,
  start: null,
  end: null,
  obstacles: new Set(),
  policy: {},
  values: {},
};

function keyOf(r, c) {
  return `${r},${c}`;
}

function parseKey(key) {
  const [r, c] = key.split(",").map(Number);
  return [r, c];
}

function currentMode() {
  const checked = document.querySelector('input[name="mode"]:checked');
  return checked ? checked.value : "start";
}

function clearPolicyAndValues() {
  state.policy = {};
  state.values = {};
}

function updateStatus(extra = "") {
  const limit = state.n - 2;
  const obstacleCount = state.obstacles.size;
  const policyCount = Object.keys(state.policy).length;
  const valueCount = Object.keys(state.values).length;
  const base = `n=${state.n}；障礙物 ${obstacleCount}/${limit}；起點：${
    state.start ? state.start.join(",") : "未設定"
  }；終點：${state.end ? state.end.join(",") : "未設定"}；策略格數：${policyCount}；價值格數：${valueCount}`;
  statusLine.textContent = extra ? `${base}｜${extra}` : base;
}

function clearCellType(r, c) {
  if (state.start && state.start[0] === r && state.start[1] === c) {
    state.start = null;
  }
  if (state.end && state.end[0] === r && state.end[1] === c) {
    state.end = null;
  }
  state.obstacles.delete(keyOf(r, c));
}

function applyClick(r, c) {
  const mode = currentMode();
  const k = keyOf(r, c);
  const obstacleLimit = state.n - 2;

  if (mode === "start") {
    clearCellType(r, c);
    state.start = [r, c];
    clearPolicyAndValues();
    updateStatus("已設定起點。地圖有變更，已清除舊策略/價值。");
    return;
  }

  if (mode === "end") {
    clearCellType(r, c);
    state.end = [r, c];
    clearPolicyAndValues();
    updateStatus("已設定終點。地圖有變更，已清除舊策略/價值。");
    return;
  }

  if (mode === "obstacle") {
    if (state.obstacles.has(k)) {
      state.obstacles.delete(k);
      clearPolicyAndValues();
      updateStatus("已移除障礙物。地圖有變更，已清除舊策略/價值。");
      return;
    }
    if (state.start && state.start[0] === r && state.start[1] === c) {
      state.start = null;
    }
    if (state.end && state.end[0] === r && state.end[1] === c) {
      state.end = null;
    }
    if (state.obstacles.size >= obstacleLimit) {
      updateStatus(`障礙物最多 ${obstacleLimit} 個。`);
      return;
    }
    state.obstacles.add(k);
    clearPolicyAndValues();
    updateStatus("已新增障礙物。地圖有變更，已清除舊策略/價值。");
  }
}

function cellClass(r, c) {
  if (state.start && state.start[0] === r && state.start[1] === c) return "start";
  if (state.end && state.end[0] === r && state.end[1] === c) return "end";
  if (state.obstacles.has(keyOf(r, c))) return "obstacle";
  return "";
}

function buildCellMarker(r, c) {
  const key = keyOf(r, c);
  if (state.obstacles.has(key)) return "■";
  if (state.end && state.end[0] === r && state.end[1] === c) return "G";
  const action = state.policy[key];
  if (action && actionToArrow[action]) return actionToArrow[action];
  return "";
}

function buildValueText(r, c) {
  const key = keyOf(r, c);
  if (state.obstacles.has(key)) return "";
  const value = state.values[key];
  if (typeof value !== "number" || Number.isNaN(value)) return "";
  return value.toFixed(2);
}

function renderGrid() {
  gridEl.innerHTML = "";
  gridEl.style.gridTemplateColumns = `repeat(${state.n}, 56px)`;

  for (let r = 0; r < state.n; r += 1) {
    for (let c = 0; c < state.n; c += 1) {
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = `cell ${cellClass(r, c)}`.trim();
      cell.dataset.r = String(r);
      cell.dataset.c = String(c);
      cell.innerHTML = `
        <span class="coord">${r},${c}</span>
        <span class="marker">${buildCellMarker(r, c)}</span>
        <span class="value">${buildValueText(r, c)}</span>
      `;
      cell.addEventListener("click", () => {
        applyClick(r, c);
        renderGrid();
      });
      gridEl.appendChild(cell);
    }
  }
}

function resetGrid(keepN = true) {
  state.start = null;
  state.end = null;
  state.obstacles.clear();
  clearPolicyAndValues();
  if (!keepN) {
    state.n = 5;
  }
  renderGrid();
  updateStatus("已重置地圖。");
}

function buildPayload() {
  return {
    n: state.n,
    start: state.start,
    end: state.end,
    obstacles: [...state.obstacles].map(parseKey),
  };
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || "API 發生錯誤");
  }
  return data;
}

async function validateGrid() {
  const result = await postJson("/api/validate-grid", buildPayload());
  updateStatus(result.message);
}

async function generatePolicy() {
  const result = await postJson("/api/generate-policy", buildPayload());
  state.policy = result.policy || {};
  state.values = {};
  renderGrid();
  updateStatus(result.message);
}

async function evaluatePolicy() {
  if (Object.keys(state.policy).length === 0) {
    updateStatus("請先產生隨機策略。");
    return;
  }

  const gamma = Number(gammaInput.value);
  const theta = Number(thetaInput.value);
  const maxIterations = Number(maxIterInput.value);

  if (!Number.isFinite(gamma) || gamma < 0 || gamma > 1) {
    updateStatus("gamma 需介於 0 到 1。");
    return;
  }
  if (!Number.isFinite(theta) || theta <= 0) {
    updateStatus("theta 必須大於 0。");
    return;
  }
  if (!Number.isInteger(maxIterations) || maxIterations <= 0) {
    updateStatus("max iterations 必須為正整數。");
    return;
  }

  const payload = {
    ...buildPayload(),
    policy: state.policy,
    gamma,
    theta,
    max_iterations: maxIterations,
  };
  const result = await postJson("/api/evaluate-policy", payload);

  state.values = result.values || {};
  renderGrid();
  updateStatus(
    `${result.message} iterations=${result.iterations}，delta=${Number(result.delta).toExponential(
      3
    )}，converged=${result.converged}`
  );
}

buildGridBtn.addEventListener("click", () => {
  const nValue = Number(nInput.value);
  if (!Number.isInteger(nValue) || nValue < 5 || nValue > 9) {
    updateStatus("請輸入 5 到 9 的整數。");
    return;
  }
  state.n = nValue;
  resetGrid(true);
});

resetBtn.addEventListener("click", () => {
  resetGrid(true);
});

validateBtn.addEventListener("click", async () => {
  try {
    await validateGrid();
  } catch (error) {
    updateStatus(`驗證失敗：${error.message}`);
  }
});

generatePolicyBtn.addEventListener("click", async () => {
  try {
    await generatePolicy();
  } catch (error) {
    updateStatus(`產生策略失敗：${error.message}`);
  }
});

evaluatePolicyBtn.addEventListener("click", async () => {
  try {
    await evaluatePolicy();
  } catch (error) {
    updateStatus(`策略評估失敗：${error.message}`);
  }
});

renderGrid();
updateStatus("可開始點擊格子設定地圖，接著產生隨機策略並做 1-2 策略評估。");
