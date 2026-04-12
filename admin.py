from flask import Blueprint, request, jsonify
from store import store

admin = Blueprint("admin", __name__, url_prefix="/admin")

REQUIRED_FIELDS = {"method", "path", "response"}


# ── Mocks ─────────────────────────────────────────────────────────────────────

@admin.post("/mocks")
def add_mock():
    """Register a new mock at runtime."""
    data = request.get_json(force=True, silent=True) or {}
    missing = REQUIRED_FIELDS - data.keys()
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(sorted(missing))}"}), 400
    return jsonify(store.add_mock(data)), 201


@admin.get("/mocks")
def list_mocks():
    """Return all registered mocks."""
    return jsonify(store.all_mocks())


@admin.delete("/mocks/<mock_id>")
def delete_mock(mock_id):
    """Remove a single mock by its id."""
    if store.remove_mock(mock_id):
        return "", 204
    return jsonify({"error": "Mock not found"}), 404


@admin.delete("/mocks")
def clear_mocks():
    """Remove all mocks."""
    store.clear_mocks()
    return "", 204


# ── Request log ───────────────────────────────────────────────────────────────

@admin.get("/requests")
def get_requests():
    """Return every request the server has received (useful for assertions)."""
    return jsonify(store.all_requests())


@admin.delete("/requests")
def clear_requests():
    """Clear the request log (call this between tests)."""
    store.clear_requests()
    return "", 204
