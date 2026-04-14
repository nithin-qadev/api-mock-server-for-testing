import uuid
import fnmatch
import threading
from datetime import datetime, timezone, timedelta


class MockStore:
    """
    In-memory store for mock definitions, recorded requests, and auth tokens.
    Thread-safe — safe to use with Flask's dev server and gunicorn workers.
    """

    def __init__(self):
        self._mocks = []
        self._requests = []
        self._tokens = {}       # token -> expiry datetime
        self._users = {}        # user_id -> user dict
        self._next_user_id = 1
        self._lock = threading.Lock()

    # ── Mock management ───────────────────────────────────────────────────────

    def add_mock(self, data):
        """Add a mock and return it with a generated id."""
        mock = {**data, "id": str(uuid.uuid4())}
        with self._lock:
            self._mocks.append(mock)
        return mock

    def remove_mock(self, mock_id):
        """Remove a mock by id. Returns True if it existed."""
        with self._lock:
            before = len(self._mocks)
            self._mocks = [m for m in self._mocks if m["id"] != mock_id]
            return len(self._mocks) < before

    def clear_mocks(self):
        with self._lock:
            self._mocks.clear()

    def all_mocks(self):
        with self._lock:
            return list(self._mocks)

    def find_mock(self, method, path):
        """
        Find the best matching mock for a given method + path.
        Last registered mock wins — makes per-test overrides easy.
        Supports fnmatch wildcards in path (e.g. /users/*).
        """
        with self._lock:
            for mock in reversed(self._mocks):
                if mock["method"].upper() == method.upper():
                    if fnmatch.fnmatch(path, mock["path"]):
                        return mock
        return None

    # ── Request log ───────────────────────────────────────────────────────────

    def log_request(self, method, path, headers, body):
        with self._lock:
            self._requests.append({
                "method": method,
                "path": path,
                "headers": headers,
                "body": body,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    def all_requests(self):
        with self._lock:
            return list(self._requests)

    def clear_requests(self):
        with self._lock:
            self._requests.clear()

    # ── Token management ──────────────────────────────────────────────────────

    def create_token(self, ttl_minutes=30):
        """Generate a new token and store it with an expiry time."""
        token = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        with self._lock:
            self._tokens[token] = expires_at
        return token, expires_at

    def is_token_valid(self, token):
        """Return True if the token exists and has not expired."""
        with self._lock:
            expires_at = self._tokens.get(token)
        if expires_at is None:
            return False
        return datetime.now(timezone.utc) < expires_at

    # ── User store ────────────────────────────────────────────────────────────

    def seed_users(self, users):
        """Load initial users on startup. Resets the store and id counter."""
        with self._lock:
            self._users = {u["id"]: u for u in users}
            self._next_user_id = max(u["id"] for u in users) + 1

    def all_users(self):
        with self._lock:
            return list(self._users.values())

    def get_user(self, user_id):
        with self._lock:
            return self._users.get(user_id)

    def create_user(self, data):
        with self._lock:
            user = {**data, "id": self._next_user_id}
            self._users[self._next_user_id] = user
            self._next_user_id += 1
            return user

    def replace_user(self, user_id, data):
        """Full update — replaces the entire user object (PUT)."""
        with self._lock:
            if user_id not in self._users:
                return None
            user = {**data, "id": user_id}
            self._users[user_id] = user
            return user

    def update_user(self, user_id, data):
        """Partial update — merges fields into existing user (PATCH)."""
        with self._lock:
            if user_id not in self._users:
                return None
            self._users[user_id] = {**self._users[user_id], **data, "id": user_id}
            return self._users[user_id]

    def delete_user(self, user_id):
        """Remove a user. Returns True if it existed."""
        with self._lock:
            return self._users.pop(user_id, None) is not None


# Single shared instance used by admin.py, dynamic.py, resources.py and server.py
store = MockStore()
