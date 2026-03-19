from flask import Flask, jsonify, render_template, request

app = Flask(__name__)


def is_valid_size(value: int) -> bool:
    return 5 <= value <= 9


@app.route("/")
def index():
    return render_template("index.html")


@app.post("/api/validate-grid")
def validate_grid():
    payload = request.get_json(silent=True) or {}
    n = payload.get("n")
    start = payload.get("start")
    end = payload.get("end")
    obstacles = payload.get("obstacles", [])

    if not isinstance(n, int) or not is_valid_size(n):
        return jsonify({"ok": False, "message": "n 必須是 5 到 9 的整數。"}), 400

    expected_obstacles = n - 2
    if not isinstance(obstacles, list):
        return jsonify({"ok": False, "message": "obstacles 必須是陣列。"}), 400

    if len(obstacles) != expected_obstacles:
        return (
            jsonify(
                {
                    "ok": False,
                    "message": f"障礙物數量需為 n-2，目前 n={n}，應為 {expected_obstacles}。",
                }
            ),
            400,
        )

    if not start or not end:
        return jsonify({"ok": False, "message": "請設定起點與終點。"}), 400

    return jsonify({"ok": True, "message": "地圖設定完成，可進入後續策略顯示與評估。"})


if __name__ == "__main__":
    app.run(debug=True)
