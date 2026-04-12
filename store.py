import uuid
import fnmatch
import threading
from datetime import datetime, timezone


class MockStore:
    """
    In-memory store for mock definitions and recorded requests.
    Thread-safe — safe to use with Flask's dev server and gunicorn workers.
    """

    def __init__(self):
        self._mocks = []
        self._requests = []
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


# Single shared instance used by admin.py and server.py
store = MockStore()
