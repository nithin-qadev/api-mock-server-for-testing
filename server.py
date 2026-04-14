import os
import time
import yaml
from flask import Flask, request, jsonify
from admin import admin
from dynamic import dynamic
from resources import resources, SEED_USERS
from store import store

app = Flask(__name__)
app.register_blueprint(admin)
app.register_blueprint(dynamic)
app.register_blueprint(resources)

ALL_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


# ── Catch-all route ───────────────────────────────────────────────────────────

@app.route("/", defaults={"path": ""}, methods=ALL_METHODS)
@app.route("/<path:path>", methods=ALL_METHODS)
def catch_all(path):
    """
    Every incoming request lands here.
    1. Log the request so tests can assert on it later.
    2. Find a matching mock (method + path).
    3. Optionally delay, then return the configured response.
    """
    full_path = f"/{path}"
    body = request.get_json(silent=True) or request.data.decode() or None
    store.log_request(request.method, full_path, dict(request.headers), body)

    mock = store.find_mock(request.method, full_path)
    if mock is None:
        return jsonify({"error": f"No mock registered for {request.method} {full_path}"}), 404

    resp = mock["response"]

    if resp.get("delay_ms"):
        time.sleep(resp["delay_ms"] / 1000)

    return jsonify(resp.get("body")), resp.get("status", 200), resp.get("headers", {})


# ── Startup ───────────────────────────────────────────────────────────────────

def load_yaml_mocks(filepath):
    if not os.path.exists(filepath):
        print(f"[mock-server] No file at '{filepath}' — starting with empty mock store.")
        return
    with open(filepath) as f:
        mocks = yaml.safe_load(f) or []
    for mock in mocks:
        store.add_mock(mock)
    print(f"[mock-server] Loaded {len(mocks)} mock(s) from '{filepath}'")


if __name__ == "__main__":
    mocks_file = os.getenv("MOCKS_FILE", "mocks/example.yaml")
    port = int(os.getenv("PORT", 8000))
    load_yaml_mocks(mocks_file)
    store.seed_users(SEED_USERS)
    print(f"[mock-server] Seeded {len(SEED_USERS)} user(s) into the user store")
    app.run(host="0.0.0.0", port=port, debug=True)
