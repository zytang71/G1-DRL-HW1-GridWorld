const gridEl = document.getElementById("grid");
const nInput = document.getElementById("grid-size");
const buildGridBtn = document.getElementById("build-grid-btn");
const resetBtn = document.getElementById("reset-btn");
const validateBtn = document.getElementById("validate-btn");
const statusLine = document.getElementById("status-line");

const state = {
  n: 5,
  start: null,
  end: null,
  obstacles: new Set(),
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

function updateStatus(extra = "") {
  const limit = state.n - 2;
  const obstacleCount = state.obstacles.size;
  const base = `n=${state.n}；障礙物 ${obstacleCount}/${limit}；起點：${
    state.start ? state.start.join(",") : "未設定"
  }；終點：${state.end ? state.end.join(",") : "未設定"}`;
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
    updateStatus("已設定起點。");
    return;
  }

  if (mode === "end") {
    clearCellType(r, c);
    state.end = [r, c];
    updateStatus("已設定終點。");
    return;
  }

  if (mode === "obstacle") {
    if (state.obstacles.has(k)) {
      state.obstacles.delete(k);
      updateStatus("已移除障礙物。");
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
    updateStatus("已新增障礙物。");
  }
}

function cellClass(r, c) {
  if (state.start && state.start[0] === r && state.start[1] === c) return "start";
  if (state.end && state.end[0] === r && state.end[1] === c) return "end";
  if (state.obstacles.has(keyOf(r, c))) return "obstacle";
  return "";
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
      cell.textContent = `${r},${c}`;
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
  if (!keepN) {
    state.n = 5;
  }
  renderGrid();
  updateStatus("已重置地圖。");
}

async function validateGrid() {
  const obstacleList = [...state.obstacles].map(parseKey);
  const payload = {
    n: state.n,
    start: state.start,
    end: state.end,
    obstacles: obstacleList,
  };

  const response = await fetch("/api/validate-grid", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const result = await response.json();
  updateStatus(result.message);
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

renderGrid();
updateStatus("可開始點擊格子設定起點、終點與障礙物。");
