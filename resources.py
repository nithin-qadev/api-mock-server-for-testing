from flask import Blueprint, request, jsonify
from store import store

resources = Blueprint("resources", __name__)

# ── Seed data ─────────────────────────────────────────────────────────────────
#
# Three pre-populated users loaded on server startup.
# Data types covered:
#   - string, int, float, bool, null
#   - nested object      → address, preferences
#   - list of strings    → tags
#   - list of ints       → lucky_numbers
#   - list of floats     → ratings
#   - array of objects   → roles (each with a permissions list), login_history

SEED_USERS = [
    {
        "id": 1,
        "name": "Alice Nguyen",
        "email": "alice@example.com",
        "age": 34,
        "active": True,
        "score": 97.4,
        "phone": "+1-555-0101",
        "address": {
            "street": "12 Maple Avenue",
            "city": "San Francisco",
            "state": "CA",
            "zip": "94103",
            "country": "US"
        },
        "tags": ["admin", "qa-lead", "automation"],
        "lucky_numbers": [3, 7, 21, 42],
        "ratings": [4.8, 4.9, 5.0, 4.7],
        "preferences": {
            "theme": "dark",
            "language": "en",
            "notifications": True,
            "timezone": "America/Los_Angeles"
        },
        "roles": [
            {"id": 1, "name": "admin",   "level": 5, "permissions": ["read", "write", "delete"]},
            {"id": 2, "name": "qa-lead", "level": 4, "permissions": ["read", "write"]}
        ],
        "login_history": [
            {"timestamp": "2026-04-01T09:00:00Z", "ip": "192.168.1.10", "success": True},
            {"timestamp": "2026-04-10T14:23:00Z", "ip": "192.168.1.10", "success": True}
        ]
    },
    {
        "id": 2,
        "name": "Bob Martinez",
        "email": "bob@example.com",
        "age": 28,
        "active": True,
        "score": 84.1,
        "phone": None,                          # null — no phone on file
        "address": {
            "street": "88 Oak Street",
            "city": "Austin",
            "state": "TX",
            "zip": "73301",
            "country": "US"
        },
        "tags": ["developer", "api-tester"],
        "lucky_numbers": [13, 27],
        "ratings": [3.9, 4.2, 4.0],
        "preferences": {
            "theme": "light",
            "language": "es",
            "notifications": False,
            "timezone": "America/Chicago"
        },
        "roles": [
            {"id": 3, "name": "developer", "level": 3, "permissions": ["read", "write"]}
        ],
        "login_history": [
            {"timestamp": "2026-03-28T08:45:00Z", "ip": "10.0.0.5", "success": False},
            {"timestamp": "2026-03-28T08:46:00Z", "ip": "10.0.0.5", "success": True},
            {"timestamp": "2026-04-11T17:00:00Z", "ip": "10.0.0.5", "success": True}
        ]
    },
    {
        "id": 3,
        "name": "Carol Smith",
        "email": "carol@example.com",
        "age": 41,
        "active": False,                        # inactive user
        "score": 62.0,
        "phone": "+1-555-0303",
        "address": {
            "street": "5 Birchwood Lane",
            "city": "Chicago",
            "state": "IL",
            "zip": "60601",
            "country": "US"
        },
        "tags": ["viewer"],
        "lucky_numbers": [1, 2, 3, 5, 8, 13],  # Fibonacci
        "ratings": [2.5, 3.0],
        "preferences": {
            "theme": "system",
            "language": "en",
            "notifications": True,
            "timezone": "America/Chicago"
        },
        "roles": [
            {"id": 4, "name": "viewer", "level": 1, "permissions": ["read"]}
        ],
        "login_history": [
            {"timestamp": "2026-01-15T10:00:00Z", "ip": "172.16.0.3", "success": True}
        ]
    }
]


# ── CRUD routes ───────────────────────────────────────────────────────────────

@resources.get("/users")
def list_users():
    return jsonify(store.all_users())


@resources.post("/users")
def create_user():
    data = request.get_json(force=True, silent=True) or {}
    return jsonify(store.create_user(data)), 201


@resources.get("/users/<int:user_id>")
def get_user(user_id):
    user = store.get_user(user_id)
    if user is None:
        return jsonify({"error": f"User {user_id} not found"}), 404
    return jsonify(user)


@resources.put("/users/<int:user_id>")
def replace_user(user_id):
    """Full update — replaces the entire user object."""
    data = request.get_json(force=True, silent=True) or {}
    user = store.replace_user(user_id, data)
    if user is None:
        return jsonify({"error": f"User {user_id} not found"}), 404
    return jsonify(user)


@resources.patch("/users/<int:user_id>")
def update_user(user_id):
    """Partial update — only the fields you send are changed."""
    data = request.get_json(force=True, silent=True) or {}
    user = store.update_user(user_id, data)
    if user is None:
        return jsonify({"error": f"User {user_id} not found"}), 404
    return jsonify(user)


@resources.delete("/users/<int:user_id>")
def delete_user(user_id):
    if not store.delete_user(user_id):
        return jsonify({"error": f"User {user_id} not found"}), 404
    return "", 204
