from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from store import store

dynamic = Blueprint("dynamic", __name__)

TOKEN_TTL_MINUTES = 30


# ── Echo ──────────────────────────────────────────────────────────────────────

@dynamic.post("/echo")
def echo():
    """
    Return the request body as-is with a UTC timestamp added.
    Useful for verifying that your framework is sending the right payload.
    """
    body = request.get_json(force=True, silent=True) or {}
    return jsonify({
        **body,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


# ── Authenticated echo ───────────────────────────────────────────────────────

@dynamic.post("/echo/secure")
def echo_secure():
    """
    Same as /echo but requires a valid Bearer token in the Authorization header.
    Returns 401 if the token is missing, malformed, or expired.
    """
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        return jsonify({
            "valid": False,
            "error": "Missing or malformed Authorization header. Expected: Bearer <token>"
        }), 401

    token = auth_header.removeprefix("Bearer ").strip()

    if not store.is_token_valid(token):
        return jsonify({"valid": False, "error": "Token is invalid or expired"}), 401

    body = request.get_json(force=True, silent=True) or {}
    return jsonify({
        **body,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


# ── Auth ──────────────────────────────────────────────────────────────────────

@dynamic.post("/auth/token")
def generate_token():
    """
    Issue a token valid for 30 minutes.
    Use the returned token as: Authorization: Bearer <token>
    """
    token, expires_at = store.create_token(ttl_minutes=TOKEN_TTL_MINUTES)
    return jsonify({
        "token": token,
        "expires_at": expires_at.isoformat(),
        "expires_in": TOKEN_TTL_MINUTES * 60     # seconds
    }), 201


@dynamic.get("/auth/validate")
def validate_token():
    """
    Validate the Bearer token from the Authorization header.
    Returns 200 if valid, 401 if missing, malformed, or expired.
    """
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        return jsonify({
            "valid": False,
            "error": "Missing or malformed Authorization header. Expected: Bearer <token>"
        }), 401

    token = auth_header.removeprefix("Bearer ").strip()

    if store.is_token_valid(token):
        return jsonify({"valid": True, "message": "Token is valid"})

    return jsonify({"valid": False, "error": "Token is invalid or expired"}), 401
