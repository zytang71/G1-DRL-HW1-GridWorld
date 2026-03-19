import random
from typing import Dict, List, Set, Tuple

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

ACTIONS: Dict[str, Tuple[int, int]] = {
    "up": (-1, 0),
    "down": (1, 0),
    "left": (0, -1),
    "right": (0, 1),
}


def is_valid_size(value: int) -> bool:
    return 5 <= value <= 9


def is_valid_coord(coord: List[int], n: int) -> bool:
    if not isinstance(coord, list) or len(coord) != 2:
        return False
    r, c = coord
    return isinstance(r, int) and isinstance(c, int) and 0 <= r < n and 0 <= c < n


def key_of(r: int, c: int) -> str:
    return f"{r},{c}"


def move(n: int, r: int, c: int, action: str, obstacles: Set[Tuple[int, int]]) -> Tuple[int, int]:
    dr, dc = ACTIONS[action]
    nr, nc = r + dr, c + dc
    if nr < 0 or nr >= n or nc < 0 or nc >= n:
        return r, c
    if (nr, nc) in obstacles:
        return r, c
    return nr, nc


def validate_and_normalize_grid(payload: dict) -> Tuple[dict, str]:
    n = payload.get("n")
    start = payload.get("start")
    end = payload.get("end")
    obstacles = payload.get("obstacles", [])

    if not isinstance(n, int) or not is_valid_size(n):
        return {}, "n 必須是 5 到 9 的整數。"
    if not is_valid_coord(start, n) or not is_valid_coord(end, n):
        return {}, "請設定合法的起點與終點座標。"
    if start == end:
        return {}, "起點與終點不可相同。"

    if not isinstance(obstacles, list):
        return {}, "obstacles 必須是座標陣列。"
    expected_obstacles = n - 2
    if len(obstacles) != expected_obstacles:
        return {}, f"障礙物數量需為 n-2，目前 n={n}，應為 {expected_obstacles}。"

    obstacle_set: Set[Tuple[int, int]] = set()
    for coord in obstacles:
        if not is_valid_coord(coord, n):
            return {}, "obstacles 含有不合法座標。"
        r, c = coord
        obstacle_set.add((r, c))

    if len(obstacle_set) != len(obstacles):
        return {}, "obstacles 內有重複座標。"

    start_t = (start[0], start[1])
    end_t = (end[0], end[1])
    if start_t in obstacle_set or end_t in obstacle_set:
        return {}, "起點或終點不可與障礙物重疊。"

    normalized = {
        "n": n,
        "start": start_t,
        "end": end_t,
        "obstacles": obstacle_set,
    }
    return normalized, ""


def generate_random_policy(n: int, end: Tuple[int, int], obstacles: Set[Tuple[int, int]]) -> Dict[str, str]:
    policy: Dict[str, str] = {}
    action_names = list(ACTIONS.keys())
    for r in range(n):
        for c in range(n):
            if (r, c) in obstacles or (r, c) == end:
                continue
            policy[key_of(r, c)] = random.choice(action_names)
    return policy


def evaluate_policy(
    n: int,
    end: Tuple[int, int],
    obstacles: Set[Tuple[int, int]],
    policy: Dict[str, str],
    gamma: float,
    theta: float,
    max_iterations: int,
) -> Tuple[Dict[str, float], int, float, bool]:
    values: Dict[str, float] = {}
    for r in range(n):
        for c in range(n):
            if (r, c) in obstacles:
                continue
            values[key_of(r, c)] = 0.0

    values[key_of(end[0], end[1])] = 0.0

    converged = False
    final_delta = 0.0

    for iteration in range(1, max_iterations + 1):
        delta = 0.0
        new_values = values.copy()

        for r in range(n):
            for c in range(n):
                if (r, c) in obstacles or (r, c) == end:
                    continue

                current_key = key_of(r, c)
                action = policy.get(current_key, "up")
                if action not in ACTIONS:
                    action = "up"

                nr, nc = move(n, r, c, action, obstacles)
                next_key = key_of(nr, nc)

                # 1-2 固定獎勵設定：每步 -1，進入終點獎勵 0。
                reward = 0.0 if (nr, nc) == end else -1.0
                updated_value = reward + gamma * values[next_key]

                delta = max(delta, abs(updated_value - values[current_key]))
                new_values[current_key] = updated_value

        values = new_values
        final_delta = delta
        if delta < theta:
            converged = True
            return values, iteration, final_delta, converged

    return values, max_iterations, final_delta, converged


@app.route("/")
def index():
    return render_template("index.html")


@app.post("/api/validate-grid")
def validate_grid():
    payload = request.get_json(silent=True) or {}
    _, error = validate_and_normalize_grid(payload)
    if error:
        return jsonify({"ok": False, "message": error}), 400
    return jsonify({"ok": True, "message": "地圖設定完成，可進入 1-2 策略顯示與價值評估。"})


@app.post("/api/generate-policy")
def generate_policy():
    payload = request.get_json(silent=True) or {}
    normalized, error = validate_and_normalize_grid(payload)
    if error:
        return jsonify({"ok": False, "message": error}), 400

    policy = generate_random_policy(normalized["n"], normalized["end"], normalized["obstacles"])
    return jsonify({"ok": True, "policy": policy, "message": "已產生隨機策略。"})


@app.post("/api/evaluate-policy")
def evaluate_policy_api():
    payload = request.get_json(silent=True) or {}
    normalized, error = validate_and_normalize_grid(payload)
    if error:
        return jsonify({"ok": False, "message": error}), 400

    policy = payload.get("policy")
    if not isinstance(policy, dict):
        return jsonify({"ok": False, "message": "請先提供策略（policy）。"}), 400

    gamma = payload.get("gamma", 0.9)
    theta = payload.get("theta", 1e-4)
    max_iterations = payload.get("max_iterations", 1000)

    if not isinstance(gamma, (float, int)) or gamma < 0 or gamma > 1:
        return jsonify({"ok": False, "message": "gamma 必須介於 0 到 1。"}), 400
    if not isinstance(theta, (float, int)) or theta <= 0:
        return jsonify({"ok": False, "message": "theta 必須大於 0。"}), 400
    if not isinstance(max_iterations, int) or max_iterations <= 0:
        return jsonify({"ok": False, "message": "max_iterations 必須為正整數。"}), 400

    values, iterations, delta, converged = evaluate_policy(
        n=normalized["n"],
        end=normalized["end"],
        obstacles=normalized["obstacles"],
        policy=policy,
        gamma=float(gamma),
        theta=float(theta),
        max_iterations=max_iterations,
    )
    return jsonify(
        {
            "ok": True,
            "values": values,
            "iterations": iterations,
            "delta": delta,
            "converged": converged,
            "message": "策略評估完成。"
            if converged
            else "達到最大迭代次數，尚未達到收斂門檻。",
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
