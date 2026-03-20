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
    if len(obstacles) > expected_obstacles:
        return {}, f"障礙物數量最多 n-2，目前 n={n}，上限為 {expected_obstacles}。"

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


def normalize_policy(
    n: int, end: Tuple[int, int], obstacles: Set[Tuple[int, int]], policy_payload: dict
) -> Dict[str, str]:
    policy: Dict[str, str] = {}
    for r in range(n):
        for c in range(n):
            if (r, c) in obstacles or (r, c) == end:
                continue
            key = key_of(r, c)
            action = policy_payload.get(key)
            if action not in ACTIONS:
                action = "up"
            policy[key] = action
    return policy


def transition_reward(
    nr: int, nc: int, end: Tuple[int, int], step_reward: float, goal_reward: float
) -> float:
    return goal_reward if (nr, nc) == end else step_reward


def evaluate_policy(
    n: int,
    end: Tuple[int, int],
    obstacles: Set[Tuple[int, int]],
    policy: Dict[str, str],
    gamma: float,
    theta: float,
    max_iterations: int,
    step_reward: float,
    goal_reward: float,
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

                reward = transition_reward(nr, nc, end, step_reward, goal_reward)
                updated_value = reward + gamma * values[next_key]

                delta = max(delta, abs(updated_value - values[current_key]))
                new_values[current_key] = updated_value

        values = new_values
        final_delta = delta
        if delta < theta:
            converged = True
            return values, iteration, final_delta, converged

    return values, max_iterations, final_delta, converged


def improve_policy(
    n: int,
    end: Tuple[int, int],
    obstacles: Set[Tuple[int, int]],
    values: Dict[str, float],
    old_policy: Dict[str, str],
    gamma: float,
    step_reward: float,
    goal_reward: float,
) -> Tuple[Dict[str, str], bool]:
    new_policy: Dict[str, str] = {}
    stable = True

    for r in range(n):
        for c in range(n):
            if (r, c) in obstacles or (r, c) == end:
                continue

            state_key = key_of(r, c)
            old_action = old_policy.get(state_key, "up")
            best_action = old_action if old_action in ACTIONS else "up"
            best_q = float("-inf")

            for action in ACTIONS:
                nr, nc = move(n, r, c, action, obstacles)
                next_key = key_of(nr, nc)
                reward = transition_reward(nr, nc, end, step_reward, goal_reward)
                q = reward + gamma * values[next_key]
                if q > best_q:
                    best_q = q
                    best_action = action

            new_policy[state_key] = best_action
            if best_action != old_action:
                stable = False

    return new_policy, stable


def train_policy_iteration(
    n: int,
    end: Tuple[int, int],
    obstacles: Set[Tuple[int, int]],
    initial_policy: Dict[str, str],
    gamma: float,
    theta: float,
    step_reward: float,
    goal_reward: float,
    max_policy_iterations: int,
    max_eval_iterations: int,
) -> Tuple[Dict[str, str], Dict[str, float], int, int, float, bool]:
    policy = initial_policy.copy()
    values: Dict[str, float] = {}
    total_eval_iterations = 0
    final_delta = 0.0
    policy_iterations = 0
    converged = False

    for outer_iter in range(1, max_policy_iterations + 1):
        values, eval_iters, delta, _ = evaluate_policy(
            n=n,
            end=end,
            obstacles=obstacles,
            policy=policy,
            gamma=gamma,
            theta=theta,
            max_iterations=max_eval_iterations,
            step_reward=step_reward,
            goal_reward=goal_reward,
        )
        total_eval_iterations += eval_iters
        final_delta = delta

        improved_policy, stable = improve_policy(
            n=n,
            end=end,
            obstacles=obstacles,
            values=values,
            old_policy=policy,
            gamma=gamma,
            step_reward=step_reward,
            goal_reward=goal_reward,
        )
        policy = improved_policy
        policy_iterations = outer_iter

        if stable:
            converged = True
            break

    return policy, values, policy_iterations, total_eval_iterations, final_delta, converged


def extract_best_path(
    n: int,
    start: Tuple[int, int],
    end: Tuple[int, int],
    obstacles: Set[Tuple[int, int]],
    policy: Dict[str, str],
) -> Tuple[List[List[int]], bool]:
    max_steps = n * n * 4
    path: List[List[int]] = [[start[0], start[1]]]
    if start == end:
        return path, True

    current = start
    visited = {start}

    for _ in range(max_steps):
        current_key = key_of(current[0], current[1])
        action = policy.get(current_key)
        if action not in ACTIONS:
            return path, False

        nr, nc = move(n, current[0], current[1], action, obstacles)
        next_state = (nr, nc)
        if next_state == current:
            return path, False

        path.append([nr, nc])
        if next_state == end:
            return path, True
        if next_state in visited:
            return path, False

        visited.add(next_state)
        current = next_state

    return path, False


@app.route("/")
def index():
    return render_template("index.html")


@app.post("/api/validate-grid")
def validate_grid():
    payload = request.get_json(silent=True) or {}
    _, error = validate_and_normalize_grid(payload)
    if error:
        return jsonify({"ok": False, "message": error}), 400
    return jsonify({"ok": True, "message": "地圖設定完成，可進入 1-2/1-3。"})


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
        policy=normalize_policy(
            normalized["n"], normalized["end"], normalized["obstacles"], policy
        ),
        gamma=float(gamma),
        theta=float(theta),
        max_iterations=max_iterations,
        step_reward=-1.0,
        goal_reward=0.0,
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


@app.post("/api/train-policy")
def train_policy_api():
    payload = request.get_json(silent=True) or {}
    normalized, error = validate_and_normalize_grid(payload)
    if error:
        return jsonify({"ok": False, "message": error}), 400

    policy_payload = payload.get("policy")
    if not isinstance(policy_payload, dict):
        return jsonify({"ok": False, "message": "請先提供初始策略（可先執行 1-2）。"}), 400

    gamma = payload.get("gamma", 0.9)
    theta = payload.get("theta", 1e-4)
    step_reward = payload.get("step_reward", -1.0)
    goal_reward = payload.get("goal_reward", 10.0)
    max_eval_iterations = payload.get("max_eval_iterations", 1000)
    max_policy_iterations = payload.get("max_policy_iterations", 200)

    if not isinstance(gamma, (float, int)) or gamma < 0 or gamma > 1:
        return jsonify({"ok": False, "message": "gamma 必須介於 0 到 1。"}), 400
    if not isinstance(theta, (float, int)) or theta <= 0:
        return jsonify({"ok": False, "message": "theta 必須大於 0。"}), 400
    if not isinstance(step_reward, (float, int)):
        return jsonify({"ok": False, "message": "step_reward 必須是數值。"}), 400
    if not isinstance(goal_reward, (float, int)):
        return jsonify({"ok": False, "message": "goal_reward 必須是數值。"}), 400
    if not isinstance(max_eval_iterations, int) or max_eval_iterations <= 0:
        return jsonify({"ok": False, "message": "max_eval_iterations 必須為正整數。"}), 400
    if not isinstance(max_policy_iterations, int) or max_policy_iterations <= 0:
        return jsonify({"ok": False, "message": "max_policy_iterations 必須為正整數。"}), 400

    initial_policy = normalize_policy(
        normalized["n"], normalized["end"], normalized["obstacles"], policy_payload
    )
    (
        trained_policy,
        values,
        policy_iterations,
        eval_iterations,
        delta,
        converged,
    ) = train_policy_iteration(
        n=normalized["n"],
        end=normalized["end"],
        obstacles=normalized["obstacles"],
        initial_policy=initial_policy,
        gamma=float(gamma),
        theta=float(theta),
        step_reward=float(step_reward),
        goal_reward=float(goal_reward),
        max_policy_iterations=max_policy_iterations,
        max_eval_iterations=max_eval_iterations,
    )
    best_path, reached_goal = extract_best_path(
        n=normalized["n"],
        start=normalized["start"],
        end=normalized["end"],
        obstacles=normalized["obstacles"],
        policy=trained_policy,
    )

    return jsonify(
        {
            "ok": True,
            "policy": trained_policy,
            "values": values,
            "best_path": best_path,
            "reached_goal": reached_goal,
            "policy_iterations": policy_iterations,
            "eval_iterations": eval_iterations,
            "delta": delta,
            "converged": converged,
            "message": (
                "1-3 訓練完成，且最佳路徑已到達終點。"
                if converged and reached_goal
                else "1-3 訓練完成，但目前策略路徑尚未到達終點。"
                if converged
                else "達到最大策略迭代次數，尚未完全收斂。"
            ),
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
